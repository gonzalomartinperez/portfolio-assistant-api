---
name: api-change-storage
description: "Implement or review PostgreSQL migrations, transaction ownership, usage reservations, checkpoint retention/deletion, or database recovery. Use for persistence guarantees and schema changes, not general retrieval relevance or deployment execution."
---

# Change persistence and recovery guarantees

Read [AGENTS.md](../../../AGENTS.md) unless already loaded. Establish target schema,
affected invariants, and whether the request permits writes. A schema review must
not apply migrations, prune data or perform a restore. Require an explicitly
isolated fixture database before destructive failure-path testing.

Inspect [migration history](../../../migrations), [migration runner](../../../app/infrastructure/migrations.py),
[storage contracts](../../../app/application), and only the affected concrete
adapter. Read [transaction/lifecycle ownership](../../../docs/architecture.md) and
[backup/upgrade procedures](../../../docs/deployment.md) for data-bearing changes.

- Preserve every applied migration and checksum; add a new ordered file. Run schema
  and checkpoint setup as explicit operator steps, never import/startup side effects.
- Each operation owns its connection/transaction. Pools are shared; a transaction
  must not be shared across concurrent tasks. Use locks/constraints to enforce
  allocation, ownership, active-run and budget races atomically. Keep SQL/driver
  errors inside infrastructure and translate failures into application errors.
- Deletion enqueues checkpoint cleanup transactionally. Keep late-write tombstones
  and bounded retries; do not claim physical deletion completed during an outage.
  Unknown provider usage must not become a free reservation.
- Recheck [runtime grants](../../../deploy/runtime-grants.sql) after schema changes.
  Runtime may mutate conversations/accounting/checkpoints but not corpus/schema;
  the maintenance profile uses separate administration credentials.

Use [maintained verification](../../../docs/local-development.md#verification):
apply migrations twice in an isolated fixture database, test checksum/order failure,
real concurrency and rollback/recovery for the changed invariant. Keep the previous
active corpus and existing data intact. For a restore drill create a new database;
never restore over an active/shared one or remove shared volumes.

Deliver migration sequence, transaction/privilege effects, backward compatibility,
actual tests and an explicit recovery procedure. Image rollback does not undo a
migration. Stop for shared/production writes or irreversible changes without current
authority; provide a reviewable procedure rather than executing it. No secrets in
commands, output, logs or committed examples.
