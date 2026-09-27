# Operations and future VPS deployment

Production deployment remains unauthorized. Main promotion requires explicit owner
approval and passing checks on its own PR.
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

## Production ownership

The private **vps-ops** repository is the sole production authority. Coolify is
selected to manage both assistant applications on the future KVM 4 VPS. This
repository supplies tested API images and the [runtime contract](deployment-contract.md).
It does not install Coolify, manage shared resources, or execute production releases.
The portfolio remains on Hostinger Business.

Existing files under `deploy/` and the disabled workflow template are retained as
**transfer references**, not a second canonical production stack. See the asset
inventory in the runtime contract. The vps-ops owner must confirm adoption before
obsolete references are retired. Application-owned local proxy tests continue to
exercise routing and streaming requirements; they do not validate Coolify itself.

## Routing, streams and browser integration

Nginx preserves `/api/v1/...` exactly; FastAPI `root_path` stays empty. `/docs`,
`/redoc`, `/openapi.json` and health paths reach FastAPI. Browser frontend requests
use relative `/api` paths; streaming goes directly to FastAPI. Public Next.js
configuration may be embedded at build time, so the frontend image must be built
for this contract; internal server URLs must never enter browser configuration.

The primary frontend is `/embed`; `/` remains a demo. Both call the API on their
own origin, so the deployment target needs only the assistant origin in the API
allowlist. Actual portfolio integration is deferred. The future parent host's
framing permission belongs to frontend/vps-ops, not API CORS. Cookie Domain stays
unset, Secure in production, SameSite=Lax; mutations require Origin and CSRF.
The retained Nginx global `frame-ancestors 'none'` is an obsolete frontend framing
assumption, not the production `/embed` policy. See [runtime contract](deployment-contract.md)
and [frontend coordination](frontend-handoff.md#embedded-experience-contract).

The edge disables SSE buffering/cache and forwards disconnects; read/send timeout
is 135 seconds, longer than the maximum 120-second run bound. SSE comment heartbeats
arrive every 15 seconds of silence without changing named events or sequence IDs.
Body size is 32 KiB; oversized requests rejected at Nginx receive 413, while direct
API validation retains its published response. Header/body read limits are ten
seconds. TLS 1.2/1.3, HSTS, nosniff and referrer headers are configured. Session,
conversation and streaming responses receive `no-store`.

Uvicorn proxy-header rewriting is disabled. Nginx overwrites client-supplied
forwarding headers; application IP accounting accepts them only from explicitly
configured trusted peer IPs. Inventory the actual proxy address after network
creation; do not trust all container or Internet addresses. An optional Cloudflare
layer needs a separate test of buffering, deadlines, cache bypass and disconnects,
plus a reviewed original-client-IP policy. It is not enabled or verified here.

## Upgrade, rollback and deployment gates

Application CI validates source and images. Authorized publication provides an
immutable digest and source revision; it does not authorize deployment. vps-ops
selects compatible frontend/backend artifacts, schedules reviewed migrations,
requires production approval and uses Coolify for deployment and verification.
No application webhook, SSH workflow or automatic deployment trigger is enabled.

Use the previous **schema-compatible** image for application rollback. Current
readiness rejects migrations unknown to that image, so a prior image is not
necessarily compatible after a schema upgrade. Database restore is a separately
reviewed procedure. A single VPS is not highly available and active streams may be
interrupted. Allow at least 25 seconds before container kill; Uvicorn drains for 15.

## Backups, monitoring and resource budget

Encrypt PostgreSQL dumps **before** copying them to access-controlled off-server
storage (for example, owner-managed age recipients and an approved object store).
Keep encryption keys independently recoverable. Schedule and alert on backup age,
failed uploads and restore drills. Retention and destination are owner decisions.
Restore into a new isolated database, verify migration checksums, knowledge version,
message/checkpoint counts, then run readiness and retrieval. Rebuild Neo4j from the
same approved public revision, or restore an offline Community dump; keep the
active corpus revision alongside the backup. A successful local pg_dump drill is
not evidence that encrypted off-server recovery works.

Initial service ceilings are API 768 MiB/1 CPU, web 512 MiB/1 CPU, PostgreSQL
1 GiB/0.75 CPU, Neo4j 2 GiB/0.75 CPU and proxy 128 MiB/0.25 CPU. These are safety
limits (~4.4 GiB total), not measured load requirements or VPS capacity promises.
Leave at least half of installed RAM available for the OS, backups and other
projects until representative measurements justify an allocation change. Run
`docker stats --no-stream` for this project's containers, collect p50/p95 request
and first-delta timing, and monitor OOM/restarts, pool saturation and disk growth.
Review capacity when sustained CPU, memory or request queues threaten the run
bounds; optimize bounded queries before adding infrastructure. JSON logs rotate at
10 MiB × three files per container. Alert on readiness loss, repeated 5xx, unknown
usage reservations, budget cutoff, cleanup backlog and storage nearing capacity.

## Deployment roadmap

1. **Application verified locally/CI:** non-root image, real-service integration,
   migrations and fixture SSE/proxy/shutdown checks. See verification records.
2. **Application handoff:** publish only after separate authorization and package
   visibility confirmation; supply digest, source SHA and runtime contract.
3. **vps-ops:** adopt transfer assets, verify Coolify digest pinning, private service
   networks, proxy routing/health checks and serialized migration execution.
4. **Owner/vps-ops gates:** registry visibility, backup retention/key custody,
   DNS/TLS authorization, encrypted restore, representative shared-VPS load and
   stream interruption/rollback tests. No production execution is authorized.

### Database role separation

The PostgreSQL initialization role (`assistant_admin` in the example) is privileged
and must **never** be used by the HTTP runtime. Its separate private migration
configuration is mounted only by the `maintenance` profile's `migrate` service.
Use `--profile maintenance run --rm migrate` for schema installation and that
service with `python -m app.knowledge_sync ...` for index administration.
After migrations, execute `deploy/runtime-grants.sql` as the schema owner. Create a
separate `assistant_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION`
role, set its password through an approved interactive secret procedure, and grant
`assistant_runtime` to it. The API uses that login. The group can read public
knowledge/migration metadata and mutate conversation/accounting/checkpoint tables;
it cannot change the corpus or schema. Re-review explicit grants for every migration.
Do not grant blanket table privileges or place administration credentials in the
long-running API container. Neo4j Community lacks the same fine-grained role model;
private network isolation and reviewed read-only query templates remain essential.
