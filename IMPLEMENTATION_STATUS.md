# Implementation status · 2026-09-27

## Scope and reconciled history

PR #6's retrieval/streaming quality pass was already merged at `492e976`; previous
pending descriptions were stale. The new work preserves that behavior and v1 wire
contract. `main` remains untouched. No paid model, production secret, VPS, DNS or
other repository working tree was used or modified.

| Increment | PR | Source commit | Develop merge |
| --- | --- | --- | --- |
| Six-layer boundaries, injected workflow, async cancellation | #7 | `d5afbba` | `85765be399ee455c44f66eff0e65fe862f9f2a92` |
| Provenance graph retrieval, indexing recovery, budgets | #8 | `ae095e5` | `b57007066d1c25f161acc14a47cbdde219776e9f` |
| Failure handling, public contracts, documentation | #9 | `94408ab`, handoff `1c0db93` | `fd3968379fc302504c9334799ff1a27cfa002360` |

Shared VPS/CI implementation is PR #10: `5438727`, paired-contract verification
`8e48bff76feca931c27d8e65e846e23e1da99411`.

## Implemented and verified locally

- Six explicit packages, architecture/import tests and strict typing of domain,
  application and AI. SQL/framework/provider details stay outside inner contracts.
- Real PostgreSQL/pgvector and Neo4j, pooled clients, durable checkpoints, atomic
  usage reservations, checksum/order migrations and recoverable public indexing.
- Incremental provider → LangGraph → SSE, citation validation, bounded input/history,
  context/output/concurrency/deadlines, cancellation/disconnect/failure/shutdown.
- Session ownership, secure-cookie configuration, exact origins/CSRF, rate limits,
  no mutation/admin HTTP tools, redacted structured request/retrieval/usage logs.
- Restricted PostgreSQL runtime grants: grounded chat and cleanup work while corpus
  writes and schema creation are denied. Administration uses a separate profile.
- Public contracts/examples, Google-derived Python conventions, verified GitHub
  private vulnerability reporting, threat model and focused contributor/runbooks.
- Shared KVM 4 Compose/proxy, no public DB ports, immutable release manifest,
  manual publishing preparation and disabled approval-gated deployment template.

Latest local full run: **56 passed in 21.44 seconds** with isolated PostgreSQL and
Neo4j. Ruff check/format, strict mypy (17 files), contract drift, Compose exposure
validation and actionlint pass. Offline selection is separate from integration.
A clean detached checkout at `94408ab` followed README installation, migrations and
pinned GitHub indexing: **52 passed in 28.03 seconds** before the latest four tests.

The production API image runs non-root/read-only. Normal SSE and active-stream
SIGTERM smoke passed; the delayed fixture was persisted as interrupted. Nginx
smoke verified paths/docs, no-store, CORS/CSRF, separate provider deltas (136 ms gap)
and disconnect interruption. Those timings are local observations, not an SLO.
The original proxy readiness test exposed an unwritable Nginx temporary directory;
all temporary paths now use tmpfs. Rollouts reload the proxy after replacement.

Redacted known-pattern history scan inspected 200 historical blobs with no findings;
it is not proof that all possible secrets are absent. A bounded independent review
found and prompted fixes for injected cleanup configuration, storage-failure event
translation, ignored public-source revision, proxy reload and runtime DB privileges.

Fixture retrieval comparisons and per-case timing are committed in
`evals/fixture-results.json`. They exercise real stores, deterministic embeddings
and public evidence; they do not measure live model answer quality. Idle isolated
PostgreSQL/Neo4j observations were approximately 44 MiB/911 MiB, excluding API,
frontend, proxy, OS and other projects. Production limits are ceilings, not load
measurements.

## CI evidence

Required Actions checks passed on PR #7 (60 seconds), #8 (80 seconds), and #9
(107 seconds). The new Quality workflow separates offline and real-service jobs,
builds once, reuses the tested image for both smoke suites, and preserves the
required `checks` aggregate without path filters. Actual run [36320177528](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/36320177528)
passed: static/offline 25 seconds, real services/container 109 seconds, aggregate
3 seconds. Both JUnit/JSON artifact bundles and the BuildKit record were retained.
This expanded scope is not a controlled speedup comparison. The final PR head
will be checked again before merge.

## Remaining release gates

- Build and HTTP proxy compatibility passed against frontend commit
  `c374aeb95484904ebdbe731a5659dc4b145d6eaf` (147.7 ms delayed-delta gap, actual
  disconnect interruption). Imported contract bytes match. Registry image digest,
  combined browser acceptance and paired immutable publishing are not yet approved.
- Live answer quality and adversarial evaluation need separate paid authorization.
  Only deterministic hash embeddings are implemented; a semantic embedding adapter
  and versioned corpus migration remain future work before semantic-vector claims.
  Fixture success does not prove prompt-injection resistance.
- TLS/certificate renewal, optional Cloudflare, trusted proxy peer inventory, actual
  Hostinger load, encrypted off-server restore, scheduled retention and upgrade /
  rollback require an authorized VPS environment. No high-availability claim.
- Owner decisions: API source license, backup destination/retention/key custody,
  ingress management and production approval. Public visibility is not a license.

Recommendation: a verified fixture backend candidate for integration on `develop`;
**not yet approved for production**. See the bounded [acceptance checklist](docs/release-checklist.md),
[frontend handoff](docs/frontend-handoff.md), [CI](docs/ci.md) and [runbook](docs/deployment.md).

A fresh local PostgreSQL dump restored into a uniquely named disposable database
matched three migrations, one active corpus, three checkpoints and message counts
in 1.32 seconds. It did not exercise encryption/off-site transport. Exact local
image IDs and diagnostic results: [verification summary](docs/verification/backend-rc.json).
