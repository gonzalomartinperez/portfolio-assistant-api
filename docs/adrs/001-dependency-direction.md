# ADR 001: application policies own their boundaries

Accepted 2026-09-27. Baseline: `492e976` (merged PR #6).

## Evidence

The API has working v1 sessions, ownership, CSRF, seven SSE events, atomic budget
reservations, checksum migrations and versioned public-source retrieval. Offline
baseline: 9 passed, 13 skipped; Ruff lint passes; formatting fails in 15 files.
There is no type checker or architecture gate. HTTP routes execute SQL and drive
LangGraph state directly. Provider creation reads global settings inside nodes.
Synchronous streaming cannot promptly cancel a blocked provider read. Existing
status text incorrectly calls merged work pending.

## Decision

Use a modular monolith under `app` with six explicit layer packages. Preserve existing CLI entry points as thin bootstrap adapters. Domain contains pure
evidence and security policies. Application owns typed workflow, provider,
retrieval and persistence contracts and use cases. `ai` implements application workflow and retrieval ports using injected capabilities.
`infrastructure` implements PostgreSQL, Neo4j, model-provider and source ports.
`presentation` translates HTTP and SSE. Bootstrap composes concrete objects
and owns their lifespan. Inner packages may import only standard library and
inner packages. AST checks enforce this rule; strict type checking starts at
these contracts and policies and expands as adapters are migrated.

Do not add an ORM, worker queue, routing model, approximate vector index or new
infrastructure. Preserve v1 paths, payloads, errors, ownership and SSE ordering.
Use async provider streaming and application events; no framework state crosses
the workflow port. Explicit time/output bounds and cancellation surround every
run. Database transactions remain local to each persistence operation.

## Sequence and acceptance

1. Capture real integration baseline and fixture timing on isolated databases;
   characterize contract, interrupted output and evidence boundaries.
2. Extract pure retrieval/context policies and typed application workflow; inject
   LangGraph, retrieval, provider and accounting adapters. Verify incremental
   output and cancellation using a gated async fake.
3. Extract conversation persistence and lifecycle orchestration from HTTP;
   compose pools/clients at lifespan and add cleanup, body/output/time limits.
4. Strengthen recoverable indexing, graph provenance and strategy evaluations;
   add migration, security and production smoke gates.
5. Publish deterministic contracts, immutable frontend handoff, threat model,
   operations and honest verification status. Integrate via checked PRs into develop.

## Sources

- https://docs.langchain.com/oss/python/langgraph/streaming (custom async events)
- https://www.psycopg.org/psycopg3/docs/advanced/pool.html (pool lifespan and transaction ownership)
- https://www.starlette.dev/responses/ (async streaming response)

Version compatibility is checked against the locked installed packages, not an
unrequested dependency upgrade. No live-model or production claims follow from
fixture tests.

## Concrete folder map (source migration)

| Package | Existing responsibilities moved here |
| --- | --- |
| `app/domain` | Pure lexical ranking, citation provenance, fixture excerpt policy from retrieval/provider |
| `app/application` | Workflow/retrieval/provider/storage ports; answer and conversation/run use cases extracted from main/workflow |
| `app/ai` | Injected LangGraph orchestration from workflow; retrieval orchestration from retrieval |
| `app/infrastructure` | psycopg DB/store/ledger/migrations; Neo4j projection; provider adapter; public Git source and indexing |
| `app/presentation` | FastAPI routes, transport models, SSE encoding and request guards from main/models |
| `app/bootstrap` | Settings, lifespan composition, CLI assembly |

`domain` imports only standard library. `application` imports standard library and
`domain`. `ai` imports these inner packages and frameworks, never concrete
infrastructure. Infrastructure implements inner ports; presentation consumes use
cases. Bootstrap is the only composition root. No empty capability packages.
Architecture tests forbid reversed imports and SQL in HTTP/application modules.

The educational purpose is explicit: keep real PostgreSQL/pgvector transactions,
Neo4j relationship traversal and LangGraph orchestration even at modest traffic.
Their operating cost includes two databases (Neo4j dominates local idle memory),
checkpoint storage and migrations. Learn one implementation of each capability;
do not add competing storage systems or independently deployed services.

## Baseline verification

The isolated real-service run passed all 22 existing tests in 19.91 seconds.
PostgreSQL/Neo4j use project `assistant-owner`, host ports 55433/57688, and separate
volumes. An initial index attempt before Neo4j readiness failed without activating
the staging corpus; retry after readiness succeeded. Source is the same pinned
public commit used by CI (`1acbe54906c88398652aebb8eae0c217fd0d8821`).
