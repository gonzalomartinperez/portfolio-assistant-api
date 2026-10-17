# ADR 005: proposed PostgreSQL consolidation within Portfolio

Status: **application implementation verified locally; production adoption pending** (2026-10-17). The owner permits
reuse within one project and prohibits sharing containers or data across projects.
This records the application-owned compatibility blueprint; it does not configure
production or replace the vps-ops composition. Existing separate fixtures remain.

## Evidence and proposed direction

Inspected application sources: API `814d04d09a276f09b52e032b0d86b8a1e4985b04` and
backoffice `d4a030a4c9a0eb0ee8161b62b8128558f22609b1`. Both use PostgreSQL 18.6;
the API image includes pgvector 0.8.7 and the IAM migration needs no vector extension.
The new isolated application proof is recorded below. The existing API Compose
initializes one assistant database; the backoffice tests use separate fresh fixtures.
Their fixture superuser credentials are not a production permission model.

Propose one project-scoped PostgreSQL instance running the API-owned
[database artifact](../../Dockerfile.postgres), with **two distinct databases** and
separate non-superuser credentials. Keep Neo4j dedicated to Portfolio's public
projection. Pequeverso, career-ops and other projects must not share this instance,
its credentials or volumes. No Redis, Celery, PgBouncer or additional service is
justified by current measurements; durable run leases, accounting and the coalescing
knowledge worker remain the current mechanisms.

The API owns the engine Dockerfile, extension compatibility and application migration
implementation. The backoffice owns Better Auth/IAM migrations. vps-ops owns effective
production composition, bootstrap execution, HBA, secrets, volumes, resource limits,
backup/restore and coordinated upgrade. This ADR is not a second production stack.
Retain the backoffice's existing PostgreSQL Dockerfile/test procedure until a tested
replacement and ownership handoff are accepted; do not remove a working fallback.

## Required database and identity boundary

Names below are implemented by the owned fixture bootstrap; they are not provisioned production resources.

| Database | Credentials and responsibilities | Runtime access |
| --- | --- | --- |
| `portfolio_assistant` | Separate API migration, runtime and knowledge-worker logins | Existing scoped corpus reads and session/checkpoint/ledger writes; worker gets only its required knowledge/accounting writes |
| `portfolio_iam` | Separate IAM migration and backoffice runtime logins | Required auth/access/audit DML only; no API corpus, conversations or ledger access |

These are databases, not two schemas in one database. PostgreSQL roles are
cluster-wide: prefix names with the project and do not grant cross-database owner
memberships. Application logins must be `NOINHERIT`, `NOSUPERUSER`, `NOCREATEDB`,
`NOCREATEROLE`, `NOREPLICATION`, `NOBYPASSRLS`. `NOINHERIT` alone is insufficient:
explicit membership/`SET ROLE` permissions must not permit reaching an owner or
another application's identity. No new row-level-security guarantee is claimed.

Revoke default `PUBLIC` database `CONNECT` and schema `CREATE` in both application
databases; grant only intended logins and required object/sequence privileges.
Review default privileges for each migration object creator so later migrations do
not silently lose runtime access or reopen public grants. Runtime users must not own
the schema or be migration users. Existing [API grants](../../deploy/runtime-grants.sql)
are only part of this contract, not a complete two-database bootstrap. Direct object
grants must reach the `NOINHERIT` runtime logins; membership in the current
`NOLOGIN assistant_runtime` group alone does not supply effective privileges.

Bootstrap pgvector in the assistant database using an approved provisioning identity
before running the non-superuser API migrator. Do not install it in IAM or hand an
extension-creation superuser to either application. The existing migration 001's
`CREATE EXTENSION IF NOT EXISTS` and checkpoint setup must be tested in this order.
Run `python -m app.migrate` and `node scripts/auth-migrate.ts` as separate one-off
image tasks, with each task's existing URL variable pointing to its own migration
identity/database. Do not change runtime credentials to migrate on startup.

HBA must match intended database/user/network tuples with SCRAM authentication and
reject cross-database access. Rule order matters; broad earlier rules must not defeat
the denies. `CONNECT` grants and HBA are complementary. Effective private network/TLS
policy and recovery access belong to vps-ops. No public database port is introduced.

## Runtime, resource and recovery implications

Existing internal PostgreSQL TCP 5432 and application health routes remain unchanged.
`DATABASE_URL` and `BACKOFFICE_DATABASE_URL` remain distinct secrets, even when their
host/port are the same. Bootstrap credentials never enter either application's
runtime environment. `pg_isready` proves server acceptance only; API corpus/schema
readiness and backoffice IAM readiness must each pass independently.

Current API pools allow 8 business and 4 checkpoint connections per process; the
backoffice allows 5. Workers, migration/backup jobs, replicas and reserved operator
connections are additional. Size the shared connection/memory budget from measured
simultaneous workloads, not only the sum 17 or the existing local `max_connections=50`.
Current separate fixture ceilings (API PG 512 MiB; IAM PG 256 MiB) do not prove a safe
shared limit or an expected memory saving. Measure RSS/PSS, query latency, lock waits,
WAL and disk growth under the same workload before selecting a production budget.

A restart, crash, storage exhaustion or engine upgrade now affects both databases.
This is a deliberate within-project failure domain, not high availability. Both apps
must tolerate transient unavailability without retrying paid generation. Drain their
work before PostgreSQL shutdown and verify the selected image's termination/restart.

Back up each database plus required cluster roles/grants and reviewed HBA/extension
metadata, encrypted off-server. Role dumps/password hashes and OAuth data are secrets;
never print or upload them as CI artifacts. Restore into a fresh isolated cluster
and verify both applications and secret recovery. Independent logical dumps do not
provide a single cross-database snapshot; document recovery points and any required
coordination rather than claiming transactional consistency between them.

Select one tested immutable engine digest through vps-ops after authorized image
publication. Rehearse patch/major upgrade, pgvector metadata, locale/collation and
both application migrations together. API pre-008 images still fail migration-history
readiness; IAM multi-version rollback is also unverified. Reverting an image does not
reverse migrations or restore either database. Preserve the separate Neo4j vendor
security blocker; PostgreSQL consolidation does not resolve it.

## Acceptance before changing the runtime handoff

The local proof below covers bootstrap, identities, real migrations, recovery and restart.
Grounded retrieval under the direct role is also a required real-service CI case.
Effective production routing/TLS, readiness, shared capacity and upgrade approval remain gates:

- Fresh non-root engine bootstrap, exact server/extension versions, distinct
  databases and isolated application identities, with no production credentials.
- Real negative tests for wrong-database connection via both HBA and `CONNECT`,
  owner membership/`SET ROLE`, runtime DDL and unintended public/default grants.
- Both real migration commands, repeated safely; runtime DML and readiness with
  non-superuser identities, including LangGraph checkpoint privileges.
- API history/ownership/cancellation/accounting and backoffice fake-OAuth membership/
  invitation/revocation tests against the same isolated engine. No paid calls or
  live OAuth/provider credentials are needed for this gate.
- Separate logical backups plus role metadata restored into a fresh cluster,
  persistent restart and graceful shutdown, and failure/recovery with one app busy.
- Rehearsed engine/extension and application upgrade/compatible rollback, exact-image
  security inventory and unchanged public/private contract checks.
- Measured shared resource/connection/lock pressure and reviewed operator runbook.

Until these pass, existing CI validates separate fixtures only. Do not claim a shared
instance was tested or update production allocation from this proposal.

References: PostgreSQL 18 [HBA rules](https://www.postgresql.org/docs/18/auth-pg-hba-conf.html),
[privileges](https://www.postgresql.org/docs/18/ddl-priv.html) and
[logical backup limits](https://www.postgresql.org/docs/18/backup-dump.html).

## Implemented application artifacts and local proof

The API image recipe now includes the idempotent
[bootstrap](../../deploy/project-postgres-bootstrap.psql) and
[ordered HBA template](../../deploy/project-pg_hba.conf). Bootstrap runs explicitly
as the local-socket-only `portfolio_bootstrap` provisioning identity; it neither
assigns passwords nor executes automatically at normal startup. Five restricted
logins receive credentials through the operator's secret-delivery procedure.
Unexpected roles, memberships, databases or owners fail closed. Re-running it
preserves existing data and passwords. The worker has its own
[exact grants](../../deploy/knowledge-worker-grants.sql).

The maintained [dual-application runner](../../scripts/verify_project_databases.py)
requires an explicit backoffice checkout and fixture authorization. It creates its
own labelled engine, volume and bridge, binds only a dynamic loopback test port,
rejects provider configuration and always removes only its verified resources.
It executes both applications' real migrations and fake-OAuth tests, runs an API
session/fixture response/history flow under the restricted identity, then tests
independent logical recovery while the other database connection remains usable.
It compares table counts/hashes after restart and after recovery into a second fresh
cluster with regenerated fixture passwords and reapplied runtime grants. No raw
auth records or archives become public artifacts. Logical dumps are not a shared
cross-database snapshot and this test does not establish recovery-time guarantees.

See [the bounded evidence and commands](../verification/project-postgres-2026-10-17.md).
The backoffice legacy PostgreSQL recipe remains intact. vps-ops must explicitly
accept this application handoff before replacing any production allocation.
