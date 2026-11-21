"""Explicit composition; imports create no network connections."""

import asyncio
import logging
import tomllib
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from decimal import Decimal
from functools import partial
from importlib import resources
from typing import TYPE_CHECKING, Any, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from neo4j import GraphDatabase
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from portfolio_assistant.adapters.clock import SystemClock
from portfolio_assistant.adapters.postgres.analytics import PostgresProductAnalytics
from portfolio_assistant.adapters.postgres.checkpoints import drain_cleanup
from portfolio_assistant.adapters.postgres.conversations import PostgresConversations
from portfolio_assistant.adapters.postgres.db import pool, translated
from portfolio_assistant.adapters.postgres.feedback import PostgresFeedback
from portfolio_assistant.adapters.postgres.ledger import EmbeddingAccounting, PostgresAccounting
from portfolio_assistant.adapters.postgres.migrations import check_schema
from portfolio_assistant.adapters.postgres.operations import OperationalObserver, PostgresOperations
from portfolio_assistant.adapters.postgres.runs import PostgresRuns
from portfolio_assistant.adapters.postgres.web_ledger import WebAccounting
from portfolio_assistant.adapters.prompts import default_prompts
from portfolio_assistant.adapters.providers.answer import (
    FixtureProvider,
    ResponsesProvider,
)
from portfolio_assistant.adapters.providers.embedding import FixtureEmbeddings, OpenAIEmbeddings
from portfolio_assistant.adapters.providers.fixture_answer import fixture_supports
from portfolio_assistant.adapters.providers.http import create_async_client, create_sync_client
from portfolio_assistant.adapters.providers.language import LocalLanguageDetector
from portfolio_assistant.adapters.providers.web_search import OpenAIWebSearch
from portfolio_assistant.adapters.retrieval import KnowledgeIndex
from portfolio_assistant.ai.retrieval import PublicRetrieval
from portfolio_assistant.ai.retrieval.rules import parse_rules
from portfolio_assistant.ai.workflow import LangGraphWorkflow
from portfolio_assistant.application.conversations import Conversations
from portfolio_assistant.application.runs import RunService
from portfolio_assistant.bootstrap.config import Settings, settings
from portfolio_assistant.bootstrap.logging import configure
from portfolio_assistant.domain.budget import Budget
from portfolio_assistant.domain.portfolio_paths import corpus_version
from portfolio_assistant.domain.web_budget import WebBudget
from portfolio_assistant.presentation.analytics import router as analytics_router
from portfolio_assistant.presentation.feedback import router as feedback_router
from portfolio_assistant.presentation.http import router
from portfolio_assistant.presentation.middleware import BodyLimit, install
from portfolio_assistant.presentation.operations import router as operations_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

    from neo4j import Driver
    from openai import AsyncOpenAI, OpenAI
    from psycopg import AsyncConnection
    from psycopg_pool import ConnectionPool

    from portfolio_assistant.adapters.observability.telemetry import PrivateTelemetry
    from portfolio_assistant.adapters.postgres.db import Connect
    from portfolio_assistant.ai.retrieval.rules import RetrievalRules
    from portfolio_assistant.application.contracts import Provider


def _load_retrieval_rules() -> RetrievalRules:
    """Read the packaged rules.toml once; the ai package itself does no file I/O."""
    text = (
        resources.files("portfolio_assistant.ai.retrieval")
        .joinpath("rules.toml")
        .read_text(encoding="utf-8")
    )
    return parse_rules(tomllib.loads(text), strict=True)


def _ready(
    connection: Connect,
    database: ConnectionPool,
    embeddings: FixtureEmbeddings | OpenAIEmbeddings,
    index: KnowledgeIndex,
) -> str | None:
    check_schema(connection)
    with database.connection() as conn:
        latest = (
            conn.cursor(row_factory=dict_row)
            .execute("SELECT max(version) AS version FROM schema_migrations")
            .fetchone()
        )
        active = (
            conn.cursor(row_factory=dict_row)
            .execute(
                "SELECT id,source_commit FROM knowledge_versions WHERE status='active' AND embedding_provider=%s AND embedding_model=%s LIMIT 1",
                (embeddings.provider, embeddings.model),
            )
            .fetchone()
        )
        if not active or active["id"] != corpus_version(
            active["source_commit"], embeddings.provider
        ):
            raise RuntimeError("corpus_unavailable")
    index.verify_ready(active["id"])
    with database.connection() as conn:
        current = (
            conn.cursor(row_factory=dict_row)
            .execute(
                "SELECT id,source_commit FROM knowledge_versions WHERE status='active' AND embedding_provider=%s AND embedding_model=%s LIMIT 1",
                (embeddings.provider, embeddings.model),
            )
            .fetchone()
        )
        if current != active:
            raise RuntimeError("corpus_changed")
    version = latest["version"] if latest else None
    return version[:3] if version else None


async def _close_resources(
    database: ConnectionPool,
    graph: Driver,
    checkpoints: AsyncConnectionPool[AsyncConnection[Any]],
    embedding_client: OpenAI | None,
    client: AsyncOpenAI | None,
    observer: OperationalObserver | None,
    runs: RunService | None,
) -> None:
    failures: list[BaseException] = []

    async def close_resource(callback: Callable[..., Awaitable[object]], *args: object) -> None:
        try:
            await callback(*args)
        except BaseException as error:  # noqa: BLE001 - Attempt every owned cleanup, then propagate all failures including cancellation.
            failures.append(error)

    # LIFO preserves drain-before-close order, including partial startup.
    async with AsyncExitStack() as stack:
        stack.push_async_callback(close_resource, asyncio.to_thread, database.close)
        stack.push_async_callback(close_resource, asyncio.to_thread, graph.close)
        stack.push_async_callback(close_resource, checkpoints.close)
        if embedding_client:
            stack.push_async_callback(close_resource, asyncio.to_thread, embedding_client.close)
        if client:
            stack.push_async_callback(close_resource, client.close)
        if observer:
            stack.push_async_callback(close_resource, observer.close)
        if runs:
            stack.push_async_callback(close_resource, runs.drain_cleanup)
    if len(failures) == 1:
        raise failures[0]
    if failures:
        raise BaseExceptionGroup("API resource cleanup failed", failures)


def _telemetry(config: Settings) -> PrivateTelemetry | None:
    if config.otel_sdk_disabled:
        return None
    from portfolio_assistant.adapters.observability.telemetry import PrivateTelemetry

    # Settings rejects a missing endpoint or revision whenever telemetry is on.
    return PrivateTelemetry(
        cast("str", config.otel_private_endpoint),
        cast("str", config.ops_api_commit),
        config.ops_trace_sample_ratio,
    )


def create_app(
    config: Settings | None = None, *, provider_override: Provider | None = None
) -> FastAPI:
    """Compose one API lifespan; a fixture-only provider override supports safe tests."""
    config = config or settings()
    configure()
    default_prompts()  # Fail fast on a stale lock or missing prompt file.
    if provider_override is not None and config.ai_provider != "fixture":
        raise ValueError("provider overrides require fixture mode")

    retrieval_rules = _load_retrieval_rules()
    clock = SystemClock()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = pool(config.database_url)
        checkpoints = AsyncConnectionPool(
            config.database_url,
            open=False,
            min_size=1,
            max_size=4,
            timeout=5,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
                "connect_timeout": 5,
            },
        )
        graph = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
            connection_timeout=2,
            connection_acquisition_timeout=3,
            max_connection_pool_size=4,
            max_transaction_retry_time=0,
            disable_auto_commit_retries=True,
            telemetry_disabled=True,
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
            if config.ai_provider == "openai":
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
                    clock=clock,
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
            embeddings: FixtureEmbeddings | OpenAIEmbeddings = FixtureEmbeddings()
            if config.embeddings_provider == "openai":
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
            app.state.feedback = PostgresFeedback(connection, clock=clock)
            app.state.knowledge = index
            # The pool's kwargs set row_factory=dict_row, which psycopg_pool's generics cannot see.
            saver = AsyncPostgresSaver(
                cast("AsyncConnectionPool[AsyncConnection[DictRow]]", checkpoints)
            )
            workflow = LangGraphWorkflow(
                PublicRetrieval(index, rules=retrieval_rules),
                provider,
                accounting,
                saver,
                detector=LocalLanguageDetector(),
            )
            app.state.conversations = Conversations(
                PostgresConversations(connection),
                config.retention_days,
                config.rate_hash_key,
                clock=clock,
            )
            if config.ops_read_token:

                @contextmanager
                def operational_connection() -> Iterator[Any]:
                    with database.connection(timeout=0.5) as conn:
                        yield conn

                operations = PostgresOperations(operational_connection, config, clock=clock)
                observer = OperationalObserver(
                    operations,
                    sample_ratio=config.ops_trace_sample_ratio,
                    exporter=_telemetry(config),
                )
                observer.start()
                app.state.operations = operations
                app.state.observer = observer

            runs = RunService(
                PostgresRuns(connection),
                workflow,
                fixture=config.ai_provider == "fixture",
                citation_support=(fixture_supports if config.ai_provider == "fixture" else None),
                timeout_seconds=config.run_timeout_seconds,
                observer=observer,
                clock=clock,
            )
            app.state.runs = runs

            app.state.ready = partial(_ready, connection, database, embeddings, index)

            def cleanup() -> None:
                try:
                    drain_cleanup(connection=connection, database_url=config.database_url, limit=1)
                except Exception:  # noqa: BLE001 - Deletion is committed; durable cleanup records must survive any adapter failure.
                    logging.getLogger("portfolio_assistant").warning(
                        '{"operation":"checkpoint_cleanup","status":"retry_pending"}'
                    )

            app.state.cleanup = cleanup
            yield
        finally:
            await _close_resources(
                database, graph, checkpoints, embedding_client, client, observer, runs
            )

    app = FastAPI(
        title="Portfolio Assistant API",
        version="1.0.0",
        lifespan=lifespan,
        telemetry={
            "tracing": False,
            "metrics": False,
            "logs": False,
            "auto_configure": False,
        },
    )
    app.state.config = config
    app.state.clock = clock
    app.state.revision = config.ops_api_commit or "unknown"
    app.add_middleware(BodyLimit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=[
            "Content-Type",
            "X-CSRF-Token",
            "X-Session-Bootstrap",
            "Idempotency-Key",
        ],
        expose_headers=["X-Run-ID", "X-Request-ID"],
    )
    install(app, config.origins)
    app.include_router(router)
    app.include_router(operations_router)
    app.include_router(analytics_router)
    app.include_router(feedback_router)
    return app
