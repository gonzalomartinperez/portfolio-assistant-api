# Project-scoped PostgreSQL application proof — 2026-10-17

This is a local WSL/Docker fixture result, not a VPS deployment or capacity claim.
Source bases: API `5a1e6af128bd744bf684b6b0f06908cca1637d89` and backoffice
`c49e11c635061e11f1b94a9495da334634e2c7d2`, with the task changes recorded in the
result's dirty-source metadata. Required CI must subsequently verify committed heads.
No paid provider, real OAuth, production data or public image publication was used.

## Executed evidence

- API offline suite: **550 passed**, 35 real-service cases deselected, 13.90 s.
- Focused fixture/architecture guards: **36 passed**, 0.72 s.
- Real project-engine permissions/migrations test: **1 passed**, 13.23 s.
- Backoffice unit suite: **94 passed**, 4.43 s; primary TypeScript **7.0.2** and
  generated Next route types passed (compiler API compatibility reports **6.0.3**).
- Real restricted IAM suite: **3 passed**, 11.69 s in the dual recovery run. Includes
  both existing fake-OAuth membership/revocation flows and runtime DDL/role denial.
- Both real migration commands repeat safely. API migrations 001–008 and checkpoint
  setup run as `portfolio_api_migrator`; IAM migration uses its own migrator with
  `--project-grants`. The provisioning identity preinstalls vector only in API DB.
- Every runtime/worker identity lacks superuser, role/database creation, replication,
  bypass-RLS, inheritance and role membership. HBA and database CONNECT deny the
  other application and maintenance databases. Wrong password, runtime DDL/TEMP,
  owner SET ROLE, unintended function execution and corpus writes are rejected.
- Actual bounded application pools were exercised separately: API eight connections,
  IAM five; exceeding each times out and releasing restores operation. This is **not**
  a simultaneous full-cohort or seventeen-connection load measurement.
- API session → conversation → fixture stream → two-message history passed under
  the direct runtime role. No corpus/Neo4j readiness is claimed by this specific run.
- Independent API/IAM dumps (**40,148 / 17,055 bytes** in the recorded fixture),
  restore with the other database connection alive, engine restart, and restore into
  a second fresh cluster preserved the compared table counts and hashes. Both
  restored runtime identities could read their required data after explicit grants.

The maintained runner writes `artifacts/project-databases.json`; the original
experimental receipt is `artifacts/project-dual-restore-receipt.json`. These are
ignored local artifacts, not a promised clean-checkout file. OAuth diagnostics use
mode 0600; archives stay in process memory. Cleanup removed owned containers,
volumes and networks. Repeatable commands, from the API checkout:

```sh
docker build -f Dockerfile.postgres -t portfolio-assistant-postgres:project-proof .
TEST_INTEGRATION=1 PROJECT_POSTGRES_IMAGE=portfolio-assistant-postgres:project-proof \
  uv run pytest -q tests/test_project_database.py
# Node 24 and frozen npm dependencies must exist in the explicitly supplied checkout.
uv run python -m scripts.verify_project_databases --authorize-fixture \
  --postgres-image portfolio-assistant-postgres:project-proof \
  --backoffice-path /path/to/portfolio-backoffice
```

The caller supplies a checkout path; there is no runtime sibling-repository import.
Read source-revision and dirty-state fields before interpreting an artifact. Use
fresh synthetic fixtures, never real keys or external database URLs. Port 3972 must
be free for the existing fake OAuth provider; the runner fails rather than stopping
another process. The exposed database port is loopback-only and fixture-specific.

## Findings fixed, not hidden

The first IAM attempt found a missing exact `rateLimit` grant required by Better
Auth 1.7.10. Adding that table preserved database-backed limiting. A second attempt
exposed the SDK's test-mode default for origin/CSRF bypass; the application now sets
both protections explicitly false for disabling them, keeping checks active in
all environments. The existing attacker-origin assertion then passed unchanged.
The initial HTTP test driver also assumed 201 and a `messages` field; it was corrected
to the already committed API's 200/`items` contract. No endpoint changed.

The first private fixture network used Docker `--internal`, which suppresses the
published loopback binding on this host. The guard rejected it. A dedicated bridge
with loopback-only publication is the test setup; production databases still have
no host-published port. Original failure logs remain ignored diagnostic evidence.

## Remaining acceptance

The API engine is PostgreSQL **18.6 Bookworm**, vector **0.8.7**; the legacy IAM
fixture uses PostgreSQL **18.6 Trixie**. Logical restore/collation review is required
before adopting the common engine. Effective private HBA/TLS, secret delivery,
backup encryption/off-server restoration, simultaneous application load, actual VPS
resource limits and upgrade/rollback rehearsals belong to the joint deployment gate.
The Neo4j Community credential boundary and vendor-image security blocker remain.
No high availability, zero downtime, live OAuth or production readiness is implied.

## Exact backoffice image extension

The same runner additionally accepted
`--backoffice-image portfolio-backoffice:project-iam-20261017-c49` and verified its
non-root source-labelled local artifact, two successful image migration tasks with
`--project-grants`, and `/api/ready` returning 200 as `portfolio_iam_runtime`.
Effective cache control was `private, no-store`; the test checks directives rather
than assuming an exact serialization. This run also repeated independent restore,
restart and fresh-cluster recovery successfully. Local manifest-list identity:
`sha256:327a103983da52228f6d52734ec8b9a468cbd748b3f38b6443fee8e7e7698f57`;
this is not a published registry digest or VPS proof. Receipt:
`artifacts/project-image-databases.json`. Images were built from the recorded task
working tree, including the pending package-version metadata change.
