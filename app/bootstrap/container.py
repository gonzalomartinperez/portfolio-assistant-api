"""Explicit composition; imports create no network connections."""

import asyncio
import logging
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from neo4j import GraphDatabase
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.adapters.postgres.analytics import PostgresProductAnalytics
from app.adapters.postgres.checkpoints import drain_cleanup
from app.adapters.postgres.conversations import PostgresConversations
from app.adapters.postgres.db import pool, translated
from app.adapters.postgres.feedback import PostgresFeedback
from app.adapters.postgres.ledger import EmbeddingAccounting, PostgresAccounting
from app.adapters.postgres.migrations import check_schema
from app.adapters.postgres.operations import OperationalObserver, PostgresOperations
from app.adapters.postgres.runs import PostgresRuns
from app.adapters.postgres.web_ledger import WebAccounting
from app.adapters.providers.answer import (
    FixtureProvider,
    ResponsesProvider,
)
from app.adapters.providers.embedding import FixtureEmbeddings, OpenAIEmbeddings
from app.adapters.providers.http import create_async_client, create_sync_client
from app.adapters.providers.language import LocalLanguageDetector
from app.adapters.providers.web_search import OpenAIWebSearch
from app.adapters.retrieval import KnowledgeIndex
from app.ai.retrieval import PublicRetrieval
from app.ai.workflow import LangGraphWorkflow
from app.application.contracts import Provider
from app.application.conversations import Conversations
from app.application.runs import RunService
from app.bootstrap.config import Settings, settings
from app.bootstrap.logging import configure
from app.domain.budget import Budget
from app.domain.web_budget import WebBudget
from app.presentation.analytics import router as analytics_router
from app.presentation.feedback import router as feedback_router
from app.presentation.http import router
from app.presentation.middleware import BodyLimit, install
from app.presentation.operations import router as operations_router


def create_app(
    config: Settings | None = None, *, provider_override: Provider | None = None
) -> FastAPI:
    """Compose one API lifespan; a fixture-only provider override supports safe tests."""
    config = config or settings()
    configure()
    if provider_override is not None and config.ai_provider != 'fixture':
        raise ValueError('provider overrides require fixture mode')

    @asynccontextmanager
    async def lifespan(app):
        database = pool(config.database_url)
        checkpoints = AsyncConnectionPool(
            config.database_url,
            open=False,
            min_size=1,
            max_size=4,
            timeout=5,
            kwargs={
                'autocommit': True,
                'prepare_threshold': 0,
                'row_factory': dict_row,
                'connect_timeout': 5,
            },
        )
        graph = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
            connection_timeout=2,
            connection_acquisition_timeout=3,
            max_connection_pool_size=4,
            max_transaction_retry_time=0,
        )
        client = None
        embedding_client = None
        runs = None
        observer = None
        try:
            await asyncio.to_thread(database.open, wait=True, timeout=10)
            await checkpoints.open(wait=True, timeout=10)
            connection = translated(database.connection)
            provider = provider_override or FixtureProvider()
            accounting = None
            if config.ai_provider == 'openai':
                # Paid authorization was validated by Settings. Never retry a possibly billed run.
                client = await create_async_client(api_key=config.openai_api_key)
                provider = ResponsesProvider(
                    client,
                    config.openai_model,
                    LocalLanguageDetector().rejects_output,
                    web_search=OpenAIWebSearch(
                        client,
                        WebAccounting(
                            connection,
                            WebBudget(
                                cutoff=Decimal(config.reserve_cutoff_usd),
                                input_price=Decimal(config.input_usd_per_million),
                                output_price=Decimal(config.output_usd_per_million),
                                fee=Decimal(config.web_search_usd_per_call),
                            ),
                        ),
                        config.web_search_timeout_seconds,
                    )
                    if config.web_search_enabled
                    else None,
                )
                accounting = PostgresAccounting(
                    connection,
                    Budget(
                        *(
                            Decimal(value)
                            for value in (
                                config.monthly_budget_usd,
                                config.reserve_cutoff_usd,
                                config.reservation_usd,
                                config.input_usd_per_million,
                                config.output_usd_per_million,
                            )
                        )
                    ),
                )
            embeddings = FixtureEmbeddings()
            if config.embeddings_provider == 'openai':
                embedding_client = create_sync_client(api_key=config.openai_api_key)
                embeddings = OpenAIEmbeddings(
                    embedding_client,
                    EmbeddingAccounting(
                        connection,
                        Decimal(config.reserve_cutoff_usd),
                        Decimal(config.embedding_usd_per_million),
                    ),
                    async_client=client,
                )
            index = KnowledgeIndex(
                connection,
                graph,
                embeddings,
                database=config.neo4j_database,
                freshness=config.knowledge_freshness_seconds
                if config.require_fresh_knowledge
                else None,
            )
            app.state.product_analytics = PostgresProductAnalytics(connection)
            app.state.feedback = PostgresFeedback(connection)
            app.state.knowledge = index
            saver = AsyncPostgresSaver(checkpoints)
            workflow = LangGraphWorkflow(
                PublicRetrieval(index),
                provider,
                accounting,
                saver,
                detector=LocalLanguageDetector(),
            )
            app.state.conversations = Conversations(
                PostgresConversations(connection),
                config.retention_days,
                config.rate_hash_key,
            )
            if config.ops_read_token:

                @contextmanager
                def operational_connection():
                    with database.connection(timeout=0.5) as conn:
                        yield conn

                operations = PostgresOperations(operational_connection, config)
                exporter = None
                if not config.otel_sdk_disabled:
                    from app.adapters.observability.telemetry import PrivateTelemetry

                    exporter = PrivateTelemetry(
                        config.otel_private_endpoint,
                        config.ops_api_commit,
                        config.ops_trace_sample_ratio,
                    )
                observer = OperationalObserver(
                    operations,
                    sample_ratio=config.ops_trace_sample_ratio,
                    exporter=exporter,
                )
                observer.start()
                app.state.operations = operations
                app.state.observer = observer

            runs = RunService(
                PostgresRuns(connection),
                workflow,
                fixture=config.ai_provider == 'fixture',
                timeout_seconds=config.run_timeout_seconds,
                observer=observer,
            )
            app.state.runs = runs

            def ready():
                check_schema(connection)
                with database.connection() as conn:
                    conn.execute('SELECT 1 FROM schema_migrations LIMIT 1')
                    if not conn.execute(
                        "SELECT id FROM knowledge_versions WHERE status='active' AND embedding_provider=%s AND embedding_model=%s LIMIT 1",
                        (embeddings.provider, embeddings.model),
                    ).fetchone():
                        raise RuntimeError('corpus_unavailable')
                graph.verify_connectivity()

            app.state.ready = ready

            def cleanup():
                try:
                    drain_cleanup(
                        connection=connection, database_url=config.database_url, limit=1
                    )
                except Exception:  # noqa: BLE001 - Deletion is committed; durable cleanup records must survive any adapter failure.
                    logging.getLogger('portfolio_assistant').warning(
                        '{"operation":"checkpoint_cleanup","status":"retry_pending"}'
                    )

            app.state.cleanup = cleanup
            yield
        finally:
            failures = []

            async def close_resource(callback, *args):
                try:
                    await callback(*args)
                except BaseException as error:  # noqa: BLE001 - Attempt every owned cleanup, then propagate all failures including cancellation.
                    failures.append(error)

            # LIFO preserves drain-before-close order, including partial startup.
            async with AsyncExitStack() as cleanup:
                cleanup.push_async_callback(
                    close_resource, asyncio.to_thread, database.close
                )
                cleanup.push_async_callback(
                    close_resource, asyncio.to_thread, graph.close
                )
                cleanup.push_async_callback(close_resource, checkpoints.close)
                if embedding_client:
                    cleanup.push_async_callback(
                        close_resource, asyncio.to_thread, embedding_client.close
                    )
                if client:
                    cleanup.push_async_callback(close_resource, client.close)
                if observer:
                    cleanup.push_async_callback(close_resource, observer.close)
                if runs:
                    cleanup.push_async_callback(close_resource, runs.drain_cleanup)
            if len(failures) == 1:
                raise failures[0]
            if failures:
                raise BaseExceptionGroup('API resource cleanup failed', failures)

    app = FastAPI(
        title='Portfolio Assistant API',
        version='1.0.0',
        lifespan=lifespan,
        telemetry={
            'tracing': False,
            'metrics': False,
            'logs': False,
            'auto_configure': False,
        },
    )
    app.state.config = config
    app.add_middleware(BodyLimit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origins,
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PATCH', 'DELETE'],
        allow_headers=[
            'Content-Type',
            'X-CSRF-Token',
            'X-Session-Bootstrap',
            'Idempotency-Key',
        ],
        expose_headers=['X-Run-ID', 'X-Request-ID'],
    )
    install(app, config.origins)
    app.include_router(router)
    app.include_router(operations_router)
    app.include_router(analytics_router)
    app.include_router(feedback_router)
    return app
