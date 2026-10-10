"""Explicit composition; imports create no network connections."""

import asyncio
import logging
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from neo4j import GraphDatabase
from openai import AsyncOpenAI, OpenAI
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.ai.retrieval import PublicRetrieval
from app.ai.workflow import LangGraphWorkflow
from app.application.contracts import Provider
from app.application.conversations import Conversations
from app.application.runs import RunService
from app.bootstrap.config import Settings, settings
from app.bootstrap.logging import configure
from app.domain.budget import Budget
from app.infrastructure.answer import (
    FixtureProvider,
    ResponsesProvider,
)
from app.infrastructure.checkpoints import drain_cleanup
from app.infrastructure.conversations import PostgresConversations
from app.infrastructure.db import pool, translated
from app.infrastructure.embedding import FixtureEmbeddings, OpenAIEmbeddings
from app.infrastructure.knowledge import KnowledgeIndex
from app.infrastructure.language import LocalLanguageDetector
from app.infrastructure.ledger import EmbeddingAccounting, PostgresAccounting
from app.infrastructure.migrations import check_schema
from app.infrastructure.runs import PostgresRuns
from app.presentation.http import router
from app.presentation.middleware import BodyLimit, install


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
        try:
            await asyncio.to_thread(database.open, wait=True, timeout=10)
            await checkpoints.open(wait=True, timeout=10)
            connection = translated(database.connection)
            provider = provider_override or FixtureProvider()
            accounting = None
            if config.ai_provider == 'openai':
                # Paid authorization was validated by Settings. Never retry a possibly billed run.
                client = AsyncOpenAI(
                    api_key=config.openai_api_key, timeout=45, max_retries=0
                )
                provider = ResponsesProvider(client, config.openai_model)
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
                embedding_client = OpenAI(
                    api_key=config.openai_api_key, timeout=20, max_retries=0
                )
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
            runs = RunService(
                PostgresRuns(connection),
                workflow,
                fixture=config.ai_provider == 'fixture',
                timeout_seconds=config.run_timeout_seconds,
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
            if runs:
                await runs.drain_cleanup()
            if client:
                await client.close()
            if embedding_client:
                await asyncio.to_thread(embedding_client.close)
            await checkpoints.close()
            await asyncio.to_thread(graph.close)
            await asyncio.to_thread(database.close)

    app = FastAPI(title='Portfolio Assistant API', version='1.0.0', lifespan=lifespan)
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
    return app
