# ADR029: Keep blocking I/O off the event loop with an async boundary ratchet

Status: accepted (2026-11-21, master plan task M4-6).

## Context and problem

The API uses a synchronous psycopg `ConnectionPool` for its stores and a separate
`AsyncConnectionPool` for the LangGraph PostgreSQL checkpointer. Async callers
offload blocking work to threads. The [target state](../master-plan/target-state.md)
calls for native async PostgreSQL access where it simplifies cancellation, and
[audit finding P2-1](../master-plan/audit.md) identifies the mixed pool usage.
The review also covers the LangSmith pin and the two metrics export paths.

## Decision drivers

- Keep blocking database, network, subprocess and shutdown work off the event loop.
- Preserve existing transaction ownership and run and ledger state guarantees.
- Make cancellation and shutdown behavior explicit and prevent the residual from growing.

## Considered options

1. **A. Keep the sync pool behind `asyncio.to_thread` with a documented residual
   and a ratchet.** Preserves the current transaction boundaries and limits where
   the default executor is used.
2. **B. Migrate all stores to `AsyncConnectionPool` now.** Enables driver-level
   async cancellation for PostgreSQL. Requires async connection and transaction
   ownership changes, cancellation review and real-store integration tests. Git,
   Neo4j and synchronous SDK cleanup would still need a separate review.
3. **C. Mix sync and async stores per adapter.** Allows incremental migration.
   During the transition, store callers would have different cancellation
   semantics and composition would still have to manage both pools.

## Decision

Choose A for M4-6. Keep all 26 references below. Each offloads blocking I/O or
resource management, so there is no trivial inline conversion. The checkpointer
continues to open and close its own pool asynchronously. A native async store
migration remains a follow-up option with real PostgreSQL tests covering
transaction rollback, run transitions, ledger writes and cancellation.

## Consequences

- Cancelling an awaiter can prevent queued work from starting. Once a worker has
  started, cancelling the awaiter does not stop it. A write already in flight
  continues through its existing transaction boundary and can commit or roll back
  on failure. Cancellation alone does not tear a run transition or ledger write,
  and the caller can lose the result even after a commit.
- The shared default executor can saturate while workers wait for connections,
  queries, subprocesses or client cleanup. Pool and operation timeouts limit
  individual waits where configured. The HTTP snapshot deadline governs the
  awaiter, and blocking reads can continue after it expires.
- Shutdown can be delayed by in-flight calls. The operational observer explicitly
  joins its shielded write before pool teardown. Executor shutdown also waits for
  running calls. Cancelling a lifespan await does not itself join the worker or
  guarantee that the next cleanup callback waits for it.

### Residual inventory

Each row represents one reference under `app/`, including the three callbacks
passed to the lifespan exit stack.

| Module | Function | Blocking operation and reason to keep | Effect of cancelling the awaiter once work starts |
|---|---|---|---|
| `app.adapters.portfolio.watch` | `PublishedPortfolio.latest` | Synchronous Git fetch and revision lookup | Git can still finish and update `FETCH_HEAD`. The watcher loses the result. |
| `app.adapters.portfolio.watch` | `PublicKnowledgePublisher.observe` | Synchronous PostgreSQL observation upsert | The observation can still commit. |
| `app.adapters.portfolio.watch` | `PublicKnowledgePublisher.publish` | Synchronous projection build and publication, including Git and storage I/O | Publication can keep running. The worker's separate stop event is checked cooperatively. |
| `app.adapters.postgres.ledger` | `PostgresAccounting.reserve` | Synchronous advisory lock, budget check and inference reservation insert | The reservation can still commit and count against the monthly cap. |
| `app.adapters.postgres.ledger` | `PostgresAccounting.settle` | Synchronous inference cost and token update | The settlement can still commit. |
| `app.adapters.postgres.operations` | `OperationalObserver._consume` | Synchronous observation insert via `store.save` | The consumer shields the write and joins it on cancellation before exiting. |
| `app.adapters.postgres.operations` | `OperationalObserver.close` | Synchronous exporter flush and shutdown | Exporter cleanup can continue after the await is interrupted. |
| `app.adapters.postgres.runs` | `PostgresRuns.start` | Synchronous transition from pending to running with a lease | The transition can still commit without returning its result. |
| `app.adapters.postgres.runs` | `PostgresRuns.history` | Synchronous conversation history query | The query can still hold a connection until it finishes. Its result is discarded. |
| `app.adapters.postgres.runs` | `PostgresRuns.running` | Synchronous run-state read | The query can still hold a connection until it finishes. Its result is discarded. |
| `app.adapters.postgres.runs` | `PostgresRuns.complete` | Synchronous row lock, assistant message insert and run completion in one transaction | The message and completion can still commit together without returning the message ID. |
| `app.adapters.postgres.runs` | `PostgresRuns.fail` | Synchronous transition to failed | The transition can still commit without returning its result. |
| `app.adapters.postgres.runs` | `PostgresRuns.interrupt` | Synchronous transition to interrupted | The transition can still commit. |
| `app.adapters.postgres.web_ledger` | `WebAccounting.reserve` | Synchronous advisory lock, budget check and web reservation insert | The reservation can still commit without returning its ID. |
| `app.adapters.postgres.web_ledger` | `WebAccounting.settle` | Synchronous web cost and token update | The settlement can still commit. |
| `app.adapters.providers.embedding` | `OpenAIEmbeddings.query` | Synchronous embedding budget reservation | The reservation can still commit without returning its ID or starting the provider request. |
| `app.adapters.providers.embedding` | `OpenAIEmbeddings.query` | Synchronous embedding usage settlement | The settlement can still commit even if the embedding result is discarded. |
| `app.adapters.retrieval` | `KnowledgeIndex.candidates` | Synchronous PostgreSQL corpus snapshot and lexical search | The reads can continue and occupy a connection. Their results are discarded. |
| `app.adapters.retrieval` | `KnowledgeIndex.candidates` | Synchronous PostgreSQL vector-neighbor query | The query can continue and occupy a connection. Its result is discarded. |
| `app.adapters.retrieval` | `KnowledgeIndex.relationships` | Synchronous Neo4j relationship reads | The reads can continue and occupy a graph session. Their results are discarded. |
| `app.bootstrap.container` | `create_app.lifespan` | Synchronous PostgreSQL pool open with a readiness wait | The open can still run while startup unwinds into cleanup. |
| `app.bootstrap.container` | `create_app.lifespan` | Synchronous PostgreSQL pool close in the exit stack | The pool close can continue after its cleanup await is interrupted. |
| `app.bootstrap.container` | `create_app.lifespan` | Synchronous Neo4j driver close in the exit stack | Driver cleanup can continue after its cleanup await is interrupted. |
| `app.bootstrap.container` | `create_app.lifespan` | Synchronous embedding client close in the exit stack | HTTP client cleanup can continue after its cleanup await is interrupted. |
| `app.presentation.operations` | `snapshot` | Synchronous PostgreSQL operational snapshot | The reads can outlive the four-second request deadline and occupy a connection. |
| `app.presentation.operations` | `snapshot` | Synchronous readiness probe using PostgreSQL and Neo4j | The probe can outlive the same request deadline and occupy backend resources. |

### Dependency review

- Keep the exact `langsmith==0.14.9` pin. LangChain Core brings LangSmith in
  as a transitive dependency, and `app/adapters/observability/evaluation_export.py` imports its
  SDK directly for the opt-in operator export. Pin bumps go through the
  [weekly dependency PR](019-weekly-dependency-pr.md). Automatic tracing remains
  disabled by the settings validator under [ADR 021](021-tracing-off-no-hosted-prompt-registry.md).
- Keep `prometheus-client` and OpenTelemetry. `prometheus-client` serves the
  private pull-based `/metrics` scrape. OpenTelemetry optionally pushes scalar
  metrics and traces over OTLP to a private endpoint. Revisit the dependency
  only if OpenTelemetry metrics replace the scrape.

## Confirmation

- [`test_async_residual.py`](../../tests/architecture/test_async_residual.py)
  checks the AST reference count per module and matches the allowances to this
  inventory. An increase or new module fails the test. A decrease requires
  lowering the allowance and removing the corresponding inventory row. Review
  enforces that allowances only decrease.
- `test_non_production_validations_report_exact_messages` in
  [`test_config_validation.py`](../../tests/unit/test_config_validation.py),
  `test_invalid_provider_or_tracing_configuration_fails_closed` in
  [`test_grounded_assistant.py`](../../tests/evals/test_grounded_assistant.py),
  and `test_global_automatic_tracing_remains_rejected` in
  [`test_evaluation_export.py`](../../tests/evals/test_evaluation_export.py)
  verify that tracing remains disabled independently of the opt-in export.
