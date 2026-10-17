# Versioned data queries — 2026-10-17

## Finite change and measured rationale

Source baseline: `ff2982783ad62be044ad4e721b8573488a9d296b` (PR80 integrated into
develop). Candidate file SHA-256 values, exact plans, profiles and all timing samples
are retained in the [synthetic receipt](database-queries-2026-10-17.json). The script
and runtime query constants are shared; the benchmark does not maintain alternative
SQL/Cypher implementations. No public, SSE, OPS or backoffice payload changed.

Two actual access paths lacked matching indexes:

- Monthly budget admission summed every retained ledger row while holding its
  existing advisory transaction lock. Migration 008 adds a B-tree on `created_at`.
  Inference, embedding and web-search accounting now share the identical UTC query
  constant; atomic admission, unsettled reservations and idempotency are unchanged.
- Graph reads filtered `Entity.version` and `Entity.normalized`; ID uniqueness did
  not index this lookup. The knowledge writer creates the composite range index,
  awaits indexes for up to30s and preserves the same supported-document query.
  No ontology, facts, relationship meaning or public entity identifiers changed.

## Representative local measurements

Python 3.14.8, WSL Linux x86_64, isolated local Compose. PostgreSQL: 0.75 CPU / 512 MiB,
`shared_buffers=128MB` / `work_mem=4MB`. Neo4j: 1 CPU / 1,536 MiB, heap 256 MiB / pagecache 256 MiB.
The final run was coordinated for 21:28:38–21:29:28 UTC, after the portfolio build ended at 21:27:33 and with vps-ops avoiding heavy local work. Load averages were recorded (4.43→3.34 one-minute). An earlier run overlapped a portfolio build and remains exploratory local evidence. This is still a shared workstation without an exclusive CPU reservation, not VPS capacity or browser performance. No durability,
fsync, transaction integrity or production read timeout was disabled.

The maintained command used five diagnostic warmups and twenty measured samples per
phase. Ledger: 100,000 synthetic rows, 500 in the current UTC month. Graph: 100 versions,
200 entities and supported documents per version; five exact names in the last
version. Answers before/after were checked equal. No paid embeddings/generation.

| Measurement | Baseline | Indexed candidate |
| --- | ---: | ---: |
| Ledger read median / sample p95 | 69.82 / 81.19 ms | 1.28 / 2.66 ms |
| Ledger plan | Sequential scan | Bitmap index/heap scan |
| Insert 1,000 median / sample p95 | 10.99 / 27.95 ms | 13.35 / 27.24 ms |
| Last insert 1,000 WAL bytes | 280,720 | 342,488 |
| Total ledger index bytes after phase | 5,775,360 | 7,634,944 |
| Graph read median / sample p95 | 97.36 / 187.94 ms | 40.34 / 96.01 ms |
| Graph access path | NodeByLabelScan | NodeIndexSeek |
| Graph PROFILE DB hits | 40,231 | 40 |

Measured index builds: PostgreSQL 133.11 ms, Neo4j 997.45 ms. Ledger write samples use
savepoints and rollback: total index bytes include physical MVCC/index churn across
phases, **not an isolated measurement of the new index's size**. Write medians varied in both directions between exploratory runs; they do not establish a write-speed gain. WAL/latency vary with
page state, scheduling and throttling. No claim that extra indexes are free, or that
these ratios generalize to other selectivities, concurrency or hardware.

An earlier exploratory run observed a two-second cold graph PROFILE timeout; it is
retained in ignored diagnostics, not discarded as success. A second exploratory run
also exposed a missing leaf `children` key in the private profile formatter; the
maintained script handles leaves with `get`, without changing the production reader.
The maintained run's first baseline PROFILE warmup took 791.50 ms. Diagnostic warmups
allow 30 s and are recorded separately; the twenty measured reads keep the production
2 s limit. These measurements do not establish worst-case cold-start behavior.
A prior maintained run recorded 71.23 MiB PostgreSQL / 690.7 MiB Neo4j idle after cleanup; not peak RSS or the final run's peak.
Neo4j index bytes and peak build memory remain unmeasured.

A separate SQL probe used 2,000 synthetic 1536D vectors across 20 versions. Existing
`chunks_version` plus exact cosine search returned the known exact vector first,
with 1.15 ms median over 20 samples. This is synthetic rank/shape correctness, **not
real-model retrieval recall**. The separate [live smoke](bounded-live-smoke-2026-10-17.md)
verified real semantic dimensions and citation provenance. No ANN, reranker, APOC,
GDS, new cache or service is justified by these small-corpus measurements.

## Reproduce safely

Use a fresh, separately owned local Compose project and unused loopback ports.
The root Compose definition remains local/CI, not a production stack. Example:

```bash
export COMPOSE_PROJECT_NAME=portfolio-query-fixture
export POSTGRES_PORT=59433 NEO4J_PORT=59688 NEO4J_HTTP_PORT=59475
export DATABASE_URL=postgresql://assistant:assistant@127.0.0.1:59433/assistant
export NEO4J_URI=bolt://127.0.0.1:59688
export AI_PROVIDER=fixture EMBEDDINGS_PROVIDER=fixture ALLOW_PAID_AI=false
mkdir -p artifacts
docker compose up --build -d --wait
uv run python -m app.migrate
uv run python -m scripts.benchmark_database_queries --seed-owned-fixtures --output artifacts/query-benchmark.json
TEST_INTEGRATION=1 uv run pytest -q tests/test_database_queries.py
```

The command never loads `.env.local`; explicit configuration and owned-container
identity/loopback checks precede writes. Existing session/corpus/ledger/operational
rows or graph nodes reject the benchmark. An actual populated-fixture invocation
was rejected without creating the requested output. `--seed-owned-fixtures` is
required; fixture mode is enforced before client use. It does not authorize use
against another developer's services.

PostgreSQL benchmark writes/DDL roll back together. Graph synthetic nodes are removed
in `finally`; the candidate index is restored, including on a query failure while
Neo4j remains reachable. A process kill/network outage can prevent cleanup: destroy
only this owned disposable Compose project/volumes after reviewing saved evidence.
Never run the benchmark during other tests on the same fixture or against production.

## Stable CI acceptance and reviewed limits

Two real-service regressions run in the existing service job, with no new CI build:

- A temporary table clones migration-defined ledger indexes, seeds 50,000 rows and
  checks the production UTC predicate chooses an index and accounts for unsettled
  costs exactly. No forced planner settings or real ledger mutation.
- An 8,192-entity version-history fixture checks the unchanged graph lookup returns
  its actual support document and stays below 1,000 PROFILE DB hits. The missing-index
  baseline scans over 16,000 hits; this margin is structural rather than a noisy
  millisecond gate. The fixture deletes only its random prefix.

Four offline cases verify explicit mutation opt-in and rejection of generation,
embedding or paid configurations before database/client validation. Existing
concurrency, ownership, FK, quota, checksum, provenance and rollback regressions
remain required. No latency threshold was weakened or introduced from a 20-sample
workstation result. The source scanner/import-cycle/negative-fixture guards still
apply; the query constants remain in infrastructure.

Backoffice IAM was separately inspected at `f05de3da681b57329d21ddab2f90ceb7a96a878c`:
lookup paths already use member primary keys and unique invitation token digests;
verified identity, invitation consumption/revocation and audit writes remain atomic.
No unmeasured index or shared-database shortcut was added there. Large IAM lists,
long-term ledger/retired-corpus growth, ANN crossover, concurrent tail latency and
VPS memory/disk capacity require a separate measured acceptance; this patch does
not certify them. Preserve existing retention and immutable citation provenance.

Read [migration/rollback requirements](../deployment-contract.md#query-index-migration-and-rollback).
Pre-008 source cannot pass strict readiness after 008; retain its migration/checksum
in a compatible forward-fix. No migration reversal or old-image compatibility is
implied. Neo4j's [vendor security blocker](neo4j-release-blocker-2026-10-17.md) remains
open independently of better query plans or green application CI.

Official references inspected:
[PostgreSQL18 EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html),
[Neo4j5 index planning](https://neo4j.com/docs/cypher-manual/5/indexes/performance-indexes/using-indexes/),
[pgvector exact and approximate search](https://github.com/pgvector/pgvector).

A fresh-fixture recheck initially failed the same graph DB-hit assertion (8,199,
threshold1,000) despite an ONLINE index. Bulk fixture loading had outpaced native
index sampling/plan-cache updates. The test now explicitly prepares statistics with
`db.prepareForReplanning(30)` after its bulk seed; it neither adds an index hint nor
relaxes the assertion. The writer also creates its initial range index **after**
the projection transaction, so first population samples actual data before PG
activation. No production cache flush/replan hook was added. Automatic sampling
and cold/cache behavior still need workload-specific verification. The recheck
passed both cases. See [Neo4j statistics and planning](https://neo4j.com/docs/operations-manual/current/performance/statistics-execution-plans/);
the exact procedure signature was also checked on the pinned 5.26 container.
