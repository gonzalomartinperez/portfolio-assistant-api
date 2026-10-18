# Common layout preflight · 2026-10-18

This is the next bounded source-layout increment after accepted analytics proof,
not a framework, contract, migration SQL, deployment or business-policy change.
Baseline API5499cf467d05e4328eaa2f51caddd14a0e266b88 and backoffice14c9e11ca42e2b47d26dc5ef55c9f0eef33512a5.
The separately frozen native proof remains site193/API596/backoffice300; moving
modules later never relabels those earlier image or browser results.

## Consumers and invariants

| Surface | Real consumer | Preservation / proof |
| --- | --- | --- |
| API ASGI | Dockerfile, retained Compose references, smoke/HTTP tests | app.main:app and existing bootstrap lifespan |
| API operator entries | CI, README, deployment/local-development commands | app.migrate, app.knowledge_sync, app.knowledge_watch, app.retention |
| Legacy settings-aware modules | Integration/benchmark/database-fixture/demo scripts | Exact db/ledger/checkpoints/migrations/indexing facades; no duplicated SQL or business implementation |
| SQL resources | Migration application and readiness guard | Exact nine existing filenames/checksums; missing resources fail closed |
| Configuration defaults | Current five legacy exceptions | Move default wiring to bootstrap; concrete adapters consume explicit values/capabilities |
| Backoffice requests | Protected pages, callbacks, Server Actions | One lazy runtime, live membership, owner authorization within transactions |
| Plain-Node operator tools | auth-migrate and fixture-session, integration tests | CLI-safe configuration/factory imports, pool cleanup and unchanged SQL URLs |
| Standalone packaging | prepare-runtime NFT trace, Dockerfile, runtime tests | Narrow relocated allowlist, both SQL files, no fixture/session tooling in image |
| Browser closure | Auth controls and shared buttons | Server Actions remain explicit; private modules rejected transitively |

Proposed API concrete packages are postgres, providers, portfolio, neo4j and
observability, plus the cohesive hybrid-retrieval adapter. Empty technology folders
and a new DI framework are not required. The five old module paths remain temporary
operator facades with no persistence/provider policy. Owner: API maintainer; removal
requires a committed operator-consumer handoff and updated runbooks/checks, not a
blanket adapters→bootstrap exception. New application code must use canonical paths.

Backoffice composition/configuration/lifecycle moves to src/server; implemented
features use domain/application/adapters/presentation; owned primitives move to
shared/ui. Framework routes and scripts/auth-migrate.ts remain stable. A CLI-safe
configuration/factory closure must not import server-only or next/headers merely
because it sits in src/server. Request-facing composition retains server-only guards.

## Pre-move regressions

The new adapter-layout tests first run against the old tree and must fail on missing
canonical placement/resource discovery. They freeze existing SQL bytes and reject
empty discovery, inward-layer legacy backedges and adapters importing bootstrap.
The five facades cannot retain SQL or concrete implementation. Add command-dispatch
positives alongside the existing real-service/operator checks after moving.

The independent read-only review identified these concrete traps:

- migrations.py currently uses parents[2]; nesting changes its root and can produce
  an empty SQL glob that falsely validates an empty history.
- Python imported functions retain their original globals. Internal monkeypatches
  must move deliberately to canonical implementation/composition modules; test
  retained exports separately, rather than duplicating code to preserve patch accidents.
- Backoffice private-module detection recognizes old auth paths. New server paths
  need negative transitive probes before movement, plus positive Server Action/UI cases.
- NFT currently accepts only features/auth. Admit only the relocated migration
  closure and retain negative private-file/fixture exclusions and image smoke.

Current graph/provider lifecycle, sessions/CSRF, budget defaults, retention limits,
public/private wire artifacts and SQL are unchanged acceptance requirements. Verify
focused regressions, the complete offline suites, real-service/image CI and actual
browser behavior. Production holds, paid-call limits and other repository ownership
remain intact. Matching folders alone is not completion.

Baseline RED command: `.venv/bin/pytest -q tests/test_adapter_layout.py` →
5 failed in0.47s on the old tree. Failures are missing canonical module/resource
locations, unknown adapter classification and concrete SQL still in the legacy
namespace. This is intentional pre-move evidence, not a passing release candidate;
the implementation must make these regressions pass before a PR is ready.
