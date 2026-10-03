# Implementation status · current increment 2026-10-03

The sections below retain historical verification. The current increment adds
continuous published-portfolio synchronization, semantic/lexical retrieval adapters,
public structured facts and starter-question contracts, local language detection,
Python 3.14, OpenAI-only GPT-6 Luna/medium configuration and migration 004/005.
See [current acceptance checkpoint](docs/work-checklist.md),
[knowledge synchronization](docs/knowledge-sync.md), and
[evaluation limitations](docs/assistant-evaluation.md).

No paid model calls, portfolio edits, image publication, main merge or production
action occurred. Current verification: **182 passed in 9.87 seconds** with real isolated databases;
Ruff, strict mypy (22 files), contract export and skill validation pass. The final
non-root image passes SSE/SIGTERM and proxy/disconnect smoke. See
[bounded evidence](docs/verification/grounded-current.json). Local fixture evaluation
covered 120 questions, 40 adversarial inputs and 27 multi-turn turns with no terminal
failures; this does not establish real model answer quality. A detached clean
checkout at 0cab0a6 passed frozen installation, 159 offline tests (23 integration
deselected), lint, typing, skill validation and contract drift.

# Historical implementation status · 2026-09-27

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

Latest local full run: **63 passed in 13.69 seconds** with isolated PostgreSQL and
Neo4j. Ruff check/format, strict mypy (17 files), contract drift, Compose exposure
validation and actionlint pass. Offline selection is separate from integration.
A clean detached checkout at `94408ab` followed README installation, migrations and
pinned GitHub indexing: **52 passed in 28.03 seconds** before the final additions. A second detached checkout at `8e48bff` passed all
56 tests then present in 8.62 seconds; seven final forwarding-header cases pass
in the latest full run.

The production API image runs non-root/read-only. Normal SSE and active-stream
SIGTERM smoke passed; the delayed fixture was persisted as interrupted. Nginx
smoke verified paths/docs, no-store, CORS/CSRF, separate provider deltas (136 ms gap)
and disconnect interruption. Those timings are local observations, not an SLO.
The original proxy readiness test exposed an unwritable Nginx temporary directory;
all temporary paths now use tmpfs. Rollouts reload the proxy after replacement.

Redacted known-pattern history scan inspected 244 historical blobs with no findings;
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

## Conversation, skills and runtime handoff increment

Source 6b1e65f; PR #19. Bounded owned history (six turns/3,000 characters), deterministic
follow-up retrieval, readable fixture prose and qualified metric citations are
implemented. Public v1 artifacts are unchanged. Local real-service suite: 83 passed.
Clean checkout: frozen install, 65 offline tests, Ruff/mypy and contract drift pass.
Actions run 36331286574 passed both parallel jobs and checks. Production image
(non-root/read-only) passed default readiness, SSE and SIGTERM; existing committed
frontend image passed Nginx routing/CORS/disconnect smoke. See
[recorded evidence](docs/verification/ux-release.json) and
[conversation before/after](docs/conversation-evaluation.md).

Five portable skills have structural tests and actual client discovery evidence;
Claude explicit expansion used a loopback transport fixture. Model-driven routing
is unverified. Coolify is selected and private vps-ops owns production; the API
[deployment contract](docs/deployment-contract.md) is the handoff. No deployment,
registry publication, paid model evaluation or production readiness claim is made.


## Consolidated backend RC continuation (2026-09-27)

- Source `57429618cf487b78842dd460411a72da45728ba0`: named-topic follow-ups,
  retained visitor refinement, target-role versus employer parsing, and fixture
  source-span attribution fixes. No new framework, schema or HTTP/SSE surface.
- Local full suite: **97 passed** with isolated PostgreSQL/pgvector and Neo4j;
  77 offline + 20 integration. Ruff, strict mypy, contract drift and skill catalog
  validation pass. Redacted scan: 353 historical blobs, no known-pattern findings
  (not proof of absence). Before/after records and limits are in
  [conversation evaluation](docs/conversation-evaluation.md).
- Committed frontend `a9a85bbf33e5ccbf8b81740b0efeb718490bd97e` protocol reviewed;
  HTTP/SSE snapshots identical. `/embed` does not require parent API CORS permission.
  Backend origin/cookie/CSRF tests pass; frontend browser validation remains separate.
- Runtime contract updated for assistant-only target origin, private immutable
  artifact planning and explicit 001–003 schema compatibility. Coolify execution
  stays with vps-ops. No production image published, credentials used or deployment.
- Skills retain one canonical source and tested discovery strategy; task guidance
  now covers topic changes and embedding ownership. Model-based skill routing and
  live-model conversational quality remain unverified.
- Latest mandate permits PR integration into develop only. Historical main merges
  do not authorize further promotion. Actual portfolio integration is deferred.
