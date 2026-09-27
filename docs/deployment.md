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

## Shared stack and server preparation

The canonical deployment specification is [`deploy/compose.yaml`](../deploy/compose.yaml).
Use a unique `COMPOSE_PROJECT_NAME=portfolio-assistant` on this shared VPS; no fixed
container names or host database ports are used. Only the optional `edge` profile
binds public ports. If an existing shared proxy or Coolify manages ingress, omit
that profile and attach its single proxy to the project's `app` network. Adapt
our reviewed routing/timeouts there; do not install a competing proxy.

Before an authorized deployment:

1. Inventory the VPS's actual CPU/RAM/disk and existing projects. Patch the OS,
   enable a firewall allowing only required public HTTP/HTTPS, and restrict SSH to
   an administrative allowlist/VPN with keys. Keep Docker socket access restricted:
   membership in its group grants host-level control. Do not expose database ports.
2. Configure the proposed DNS and TLS only after owner authorization. Mount a
   protected certificate directory containing `fullchain.pem` and `privkey.pem`;
   arrange renewal and an Nginx reload. The unprivileged proxy UID must be able to
   read the key without making it world-readable. Test TLS renewals separately.
3. Copy the examples under `deploy/` into private files outside the checkout,
   mode 0600. Provision strong distinct DB credentials and a random rate-hash key.
   Model credentials remain absent in fixture mode. Register exact assistant and
   portfolio origins, secure host-scoped cookies, and actual proxy peer addresses.
   Do not render `docker compose config` with real secrets into logs.
4. Authenticate to the image registry with a minimally scoped pull credential.
   Select a reviewed manifest containing both full source SHAs and image digests.
   The frontend owner must supply its committed production image handoff first.
5. From the repository root, set the private Compose environment file and run
   `docker compose --env-file /private/compose.env -f deploy/compose.yaml up -d postgres neo4j`.
   Run the maintenance image once with `python -m app.migrate`, then
   `python -m app.knowledge_sync --source github --ref <approved-full-public-SHA>`.
   The private API environment must point at Compose service names, not localhost.
6. Start API/web with `up -d --wait api web`, then enable the single edge proxy with
   `--profile edge up -d proxy` (or configure the approved existing ingress).
   Run `python3 -m scripts.deployment_smoke https://assistant.gonzalomartinperez.com`.
   This creates/deletes a temporary anonymous session and checks deterministic stop-word-only
   SSE without paid model use. Also verify a grounded fixture chat and browser UI.

The API image writes only `/tmp`; PostgreSQL and Neo4j persist in their named data
volumes. The frontend owner’s committed handoff specifies a 32 MiB tmpfs at
`/app/.next/cache`, UID/GID 1000, mode 0700; the shared stack includes it. Never use `down -v` for upgrades.

## Routing, streams and browser integration

Nginx preserves `/api/v1/...` exactly; FastAPI `root_path` stays empty. `/docs`,
`/redoc`, `/openapi.json` and health paths reach FastAPI. Browser frontend requests
use relative `/api` paths; streaming goes directly to FastAPI. Public Next.js
configuration may be embedded at build time, so the frontend image must be built
for this contract; internal server URLs must never enter browser configuration.

The existing portfolio has a native assistant panel making credentialed API calls,
plus a standalone link; it does not embed an iframe. Allow exactly
`https://gonzalomartinperez.com` and `https://assistant.gonzalomartinperez.com`.
Sharing a parent domain does not remove CORS or CSRF requirements. Cookie domain is
unset (host-only), Secure in production, SameSite=Lax. Mutations require the allowed
Origin and session CSRF token. Framing is disallowed by `frame-ancestors 'none'`.

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

Active CI never deploys. The disabled workflow template, required environment
review, and immutable publishing are described in [CI](ci.md). An authorized
operator can run `deploy/apply-release.sh --approved release.json /private/compose.env`
only after recording a backup/restore receipt and reviewing migration compatibility.
Serialize deployments; preserve the preceding manifest and images. Reload the
single proxy after container replacement so it resolves new upstream addresses.
For externally managed ingress, its reload belongs to the approved transport.
Run readiness and actual public SSE after the rollout. If code is incompatible,
stop and use the previous schema-compatible image pair; do not blindly roll back
schema. A single VPS is not highly available; active streams may be interrupted
and upgrades can cause downtime. SIGTERM permits 15 seconds before cancellation;
the container stop allowance is 25 seconds.

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

1. **Implemented:** shared Compose/proxy, immutable manifest validation, non-root
   API build, local proxy/stream checks and parallel repository CI.
2. **Frontend coordination:** committed production image digest/revision, relative
   browser URLs, cache paths and standalone image smoke from its owner; run the
   combined browser journey before accepting a paired candidate.
3. **Owner decisions:** license, backup destination/retention/key custody, shared
   ingress management (plain Compose or optional Coolify), registry policy.
4. **Authorized VPS verification:** provision/harden, DNS/TLS, encrypted restore,
   Cloudflare if selected, representative multi-project load and active-stream
   upgrade/rollback. Only then approve a production environment and activate CD.

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
