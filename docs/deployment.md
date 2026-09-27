# Operations and future VPS deployment

No production deployment or `main` promotion is performed by this project work.
The target is Hostinger VPS KVM 4, shared with the assistant frontend and other projects; the existing portfolio remains on Hostinger Business. The shared proxy routes / to Next.js and preserves /api/* for FastAPI. PostgreSQL/pgvector and Neo4j remain private. No additional managed Node.js slot is used.
No queue service, Kubernetes or heavyweight telemetry platform is required.

## Start and upgrade

1. Back up PostgreSQL to encrypted storage and verify a restore before data-bearing
   upgrades. Record the API image digest, source commit and active corpus revision.
2. Build from a clean locked checkout (`uv sync --frozen`; pinned Docker base images).
   The image runs as UID/GID 65532, with no root privileges required. Run with a
   read-only filesystem and writable temporary directory where supported.
3. Run `python -m app.migrate` as an explicit one-shot operator step. Migration
   filenames/order/checksums are validated under a transaction lock. Never edit an
   applied file or recreate a database to pass a check. Checkpoint setup follows
   application migrations and is not an HTTP startup operation.
4. Index the approved immutable public commit. PostgreSQL becomes active only after
   both projections verify. A failed staging version can be retried; it does not
   replace the last valid corpus.
5. Start the API. `/health/live` checks process response; `/health/ready` requires
   schema, active corpus and graph connectivity. Run the public session/SSE smoke
   before switching traffic. Keep the previous image and backup for rollback.

Roll back code to a verified compatible image; for an incompatible data migration,
restore the verified PostgreSQL backup into a separate instance and explicitly
switch after validation. Do not run destructive down migrations or overwrite the
live database as an automatic rollback.

## Network and security

Set `ENVIRONMENT=production`, TLS browser origins, `SECURE_COOKIES=true`, explicit
private DB/graph credentials and a random rate hash key. Trust only the actual
reverse proxy peer IPs. Keep database ports private. Limit request body size and
header/body-read time at the proxy. Disable buffering/cache for POST SSE; allow a
read timeout longer than the run deadline. SameSite=Lax requires a same-site web/API
deployment; unrelated domains require coordinated cookie changes before release.

The image uses Uvicorn's 15-second graceful shutdown allowance. Long active runs are
cancelled after that allowance; cleanup closes the workflow/provider and records
interruption where storage is available. Expired five-minute leases are reconciled
when runs are next accessed. Never replay an uncertain billed run automatically.
Provider requests use a 45-second SDK timeout and no automatic retries; SQL has
connect/lock/statement bounds, and graph traversal uses a two-second query timeout.

## Retention, privacy and scheduled work

Run `python -m app.retention` every minute under the same private configuration.
It purges expired anonymous sessions and old rate hashes, and retries at most 100
checkpoint cleanup records. Deletion responses attempt one bounded cleanup item;
tombstones remain ten minutes to handle late cancelling checkpoint writes. During a
DB outage physical deletion waits for recovery. Monitor cleanup warnings and queue
age. Budget totals retain amount/time after their run reference is removed.
Do not delete staging/retired corpora automatically; review disk growth and retain
only revisions needed for rollback through an explicit operator procedure.

## Backup and restore

For a local drill, use a restricted directory and a dedicated test database:

```sh
umask 077
docker compose exec -T postgres pg_dump -U assistant -Fc assistant > /private/assistant.dump
docker compose exec -T postgres createdb -U assistant assistant_restore
cat /private/assistant.dump | docker compose exec -T postgres pg_restore -U assistant -d assistant_restore --exit-on-error
```

Choose an unused restore database name; never restore over the active database.
Verify schema_migrations, sessions/messages, active knowledge/source hashes and
checkpoints, then run readiness/retrieval against the restored instance. Production
backups need encryption, access control, off-site copies, retention and periodic
restore drills. Neo4j is rebuildable from the approved source; Community also
supports an **offline** `neo4j-admin database dump`. Do not promise online Community
backup. Operator downtime and backup deletion policy require a release decision.

## Observability and capacity

Structured JSON logs expose generated request correlation, route/status, total
stream duration, first-delta latency, source counts, selected retrieval strategy,
failures and known provider tokens/cost. They omit questions, answers, cookies,
credentials, prompt text and raw dependency errors. No external tracer is enabled
by the fixture script or image. Collect stdout with modest rotation; alert on 5xx,
readiness failure, long streams, cleanup backlog, near-budget totals and disk usage.

Baseline local fixture HTTP totals were 788–1764 ms for three questions, with a
1628 ms median, using buffered TestClient (not first-delta timing). Historical idle
API/web/PostgreSQL/Neo4j containers totaled about 874 MiB; that includes another
repository's web measurement and is not a current VPS claim. Current backend-only
observations are recorded in implementation status. Representative load, proxy
behavior, TLS and actual Hostinger capacity remain release gates.
