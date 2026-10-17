# API runtime handoff to vps-ops

Status: application contract, not deployment authorization. Coolify is selected
for the future Hostinger KVM 4 VPS and managed only through private vps-ops.
The portfolio remains on Business. No Coolify installation or production test has
been performed here. Baseline source snapshot: `9fe079a34f822f56aa2fea0741088721c28bdcf5`.
The commit containing this document identifies the handoff revision.

## Artifact and runtime

Build locally: `docker build --platform linux/amd64 -t portfolio-assistant-api:local .`.
CI currently verifies Linux amd64 only. The candidate publisher prepares
`ghcr.io/gonzalomartinperez/portfolio-assistant-api:<full-source-SHA>` and records
its immutable registry manifest `@sha256:` digest (not a local image ID).
Publication is not yet authorized; plan private package visibility unless separately
authorized and provision pull access through vps-ops. Consume
tested prebuilt digests, not source builds on the VPS.

The image runs as UID/GID 65532 in `/app`, binding `0.0.0.0:8000` internally:

```sh
uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log --no-proxy-headers --timeout-graceful-shutdown 15
```

Use the explicit `--no-proxy-headers` runtime option: application trust checks,
not Uvicorn rewriting, own client-IP accounting. No public API host-port binding
is needed. Only the vps-ops proxy exposes traffic. Startup opens bounded PostgreSQL
and checkpoint pools; dependencies must already exist. It does not run migrations
or ingest a corpus. Shutdown closes provider, pools and graph clients. Allow at
least 25 seconds before SIGKILL; active runs can be interrupted after 15 seconds.

Use a read-only root filesystem, writable `/tmp`, dropped capabilities and
no-new-privileges where supported. The API needs no persistent container volume.
PostgreSQL and Neo4j data durability is owned by vps-ops.

The image uses separate dependency and runtime stages with the frozen production
lock. `uv`/`uvx`, pip, ensurepip and development dependencies are absent from runtime. Git remains
necessary for the approved public-corpus CLI/worker. SIGTERM is explicit; before
closing storage, lifespan interrupts remaining active run IDs and drains tracked interruption
writes for up to five seconds. A failed/timed-out cleanup relies on the existing persisted lease and
retention reconciliation, not a successful-answer claim.


## Configuration and secrets

All API configuration is runtime configuration; no build-time secrets or public
configuration embedding. [Environment reference](environment.md) lists types,
defaults and validation bounds. Production requires `ENVIRONMENT=production`,
`SECURE_COOKIES=true`, explicit `ALLOWED_ORIGINS`, `DATABASE_URL`, `NEO4J_URI`,
`NEO4J_USER`, `NEO4J_PASSWORD`, and random `RATE_HASH_KEY` of at least 32 characters.
Set exact `TRUSTED_PROXY_IPS` after peer discovery. Keep `AI_PROVIDER=fixture`,
`EMBEDDINGS_PROVIDER=fixture`, `ALLOW_PAID_AI=false` until separately authorized.

Secret names: `DATABASE_URL` (contains password), `NEO4J_PASSWORD`, `RATE_HASH_KEY`,
and optional authorized `OPENAI_API_KEY`. Supported delivery is process environment
(or a private `.env.local` parsed by settings); native `_FILE` variables are not
implemented. vps-ops/Coolify must deliver environment secrets without logging their
values. Do not supply them as Docker build arguments or publish rendered configs.
Keep administration credentials out of the long-running API. Settings validation hides input values in rendered errors; nevertheless do not copy
configuration objects or structured validation details into logs or CI artifacts. Public request errors are translated/redacted.

## Services and migrations

Tested services: PostgreSQL 18.6 with pgvector 0.8.7; Neo4j5.26.32 Community Trixie retained baseline (current patch in the5.26 LTS line).
The application uses Python 3.14.8 and the build uses uv 0.13.1, each pinned by
immutable upstream image digest. These are same-line patch updates; they are not
authorization to upgrade production stores. vps-ops must back up and rehearse
restoration before replacing a Neo4j image; no zero-downtime or reverse store
compatibility is claimed. The retained deploy/ transfer reference is not the
canonical production stack and has not been silently rewritten.
See locked Python dependencies and pinned local Compose images for exact versions.
Private TCP access to PostgreSQL 5432 and Neo4j Bolt 7687 is required. Fixture
chat requires no external model network; approved indexing uses GitHub HTTPS,
and separately authorized OpenAI mode requires provider HTTPS egress. No shell,
write or arbitrary browsing capability is exposed to the assistant.

vps-ops schedules one-shot `python -m app.migrate` using the same image and separate
schema-owner credentials before API readiness. Application SQL files run in order
under an advisory transaction lock with checksum/prefix validation. LangGraph
checkpoint setup runs afterward in a separate connection: the complete operation
is not one atomic transaction. Retry the same image after resolving failure; never
edit an applied migration. Apply reviewed runtime grants from
`deploy/runtime-grants.sql` after schema/checkpoint creation. Index only an approved
public immutable revision with `python -m app.knowledge_sync --source github --ref
<full-SHA>` before initial readiness. Run `python -m app.retention` every minute
under appropriate private configuration; scheduling belongs to vps-ops.

Current application schema includes ordered migrations 001–006, plus the locked
LangGraph checkpoint schema. Migration 004 adds semantic vectors, lexical search,
embedding identity, freshness state and a single-active-version constraint. Migration 005 persists public embeddings after each successful call for crash-safe
reuse. Apply both before starting this image. Older images reject unknown applied migrations;
image-only rollback to the previous release is not compatible without a separately
reviewed recovery path. Reapply reviewed runtime grants including SELECT on
knowledge_watch. The worker uses separate corpus/ledger write credentials.

**Rollback limitation:** readiness rejects unknown applied migrations. Older images
may therefore be incompatible after an upgrade even when tables are additive.
Review each image/schema pair explicitly; never assume overlapping old/new versions
or automatic down migrations. Backups and restore into a separate database require
a separately tested recovery procedure.

## Health, routing and streams

- `GET /health/live`: process response, not dependency readiness.
- `GET /health/ready`: schema/checksum, active public corpus matching the configured embedding model and graph connectivity;
  use as the traffic admission probe. No paid model call.
- Suggested container probe: `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)"`.
  Initial settings: interval 20s, timeout 8s, retries 3, start period 30s; verify on VPS.

Preserve `/api/v1/...` verbatim. FastAPI `root_path` is empty: never strip/add `/api`.
Route `/` to the authenticated backoffice; the native chat belongs to the separate
portfolio origin. The backoffice does not serve `/embed`. Docs `/docs`, `/redoc`,
`/openapi.json` and `/health/*` require
explicit API routing or restricted administrative access. The API contract artifacts
remain authoritative. vps-ops must verify the exact Coolify routing configuration.

Disable SSE buffering and caching; propagate disconnects. Heartbeat comments occur
after 15 seconds of silence. Proxy read/send timeout must exceed maximum run bound
120 seconds (reference uses 135). Body limit reference is 32 KiB; proxy rejection
is 413. Preserve `no-store` for sessions/conversations/streams. Overwrite untrusted
forwarding headers and configure exact trusted peers. TLS/security headers and any
Cloudflare layer require separate end-to-end verification.

Host-only Secure HttpOnly SameSite=Lax `__Host-assistant_session` has no Domain
attribute. Mutations still require allowed Origin and CSRF token. The current native portfolio target requires the explicitly approved origin
`https://gonzalomartinperez.com` in `ALLOWED_ORIGINS`, with credentialed CORS and
unchanged CSRF enforcement. The portfolio's committed client constructs paths
under the separately configured assistant API origin. Add other origins only after
review; a shared parent domain does not remove cross-origin requirements. The
assistant remains disabled in the portfolio and production integration is untested.
The former `/embed` plan below is historical, superseded by the native UI and
authenticated backoffice decision; it must not drive current proxy/framing setup.

Historical iframe guidance (not the current native integration):
frontend/vps-ops own the `/embed` framing policy and exact parent allowlist. Do not
copy the frozen Nginx template's global `frame-ancestors 'none'` onto that frontend
route. API routes can retain anti-framing headers. Do not broaden CORS, cookie Domain
or SameSite merely to support an iframe. The proposed HTTPS parent and assistant
share a site; unrelated-site embedding is unsupported and requires separate browser
privacy/security review. No production iframe or browser-cookie verification is claimed.
See the [frontend handoff](frontend-handoff.md#embedded-experience-contract).

## Evidence and verification

Local/CI image and Nginx fixture tests are recorded in IMPLEMENTATION_STATUS.md and
[CI](ci.md); they are not Coolify tests. Historical local idle stack measurement
~874 MiB included web and both databases; not a VPS guarantee. Previous proposed
resource ceilings are retained only as transfer inputs in deployment.md. vps-ops
owns final measurement/allocation. Structured application stderr logs include correlation, latency,
retrieval strategy/count and usage; omit raw prompts, answers and dependency errors.
Rotation/collection belongs to vps-ops.

After authorized local startup, run `uv run python -m scripts.deployment_smoke
http://127.0.0.1:<isolated-port>` for session/CSRF/terminal SSE checks; also run a
grounded fixture chat, cancellation and readiness loss/recovery checks. Local
container tests in `scripts/container_smoke.py` exercise the production image.
Coolify must additionally verify immutable digest selection, probe routing,
shutdown during a stream and schema-compatible rollback. No zero-downtime claim.

## Ownership transfer inventory

| Assets | Classification / next owner |
| --- | --- |
| Dockerfile, .dockerignore, lockfiles, .env.example, app migrations, contracts, active quality/publish workflows | Retain: application-owned |
| Root compose.yaml, scripts/fixture-env.sh, container/proxy smoke scripts | Retain: isolated local/CI verification |
| deploy/compose.yaml, deploy/nginx/*, deploy/*env.example | Frozen shared-production transfer references; vps-ops confirms adoption before retirement |
| deploy/apply-release.sh, .github/workflow-templates/deploy-vps.yml | Inactive transfer references; do not execute/activate here or create a competing controller |
| deploy/runtime-grants.sql | Retain reviewed application schema privileges; vps-ops schedules execution |

Open vps-ops decisions: exact Coolify version/resource type and digest workflow,
private pull access/package visibility, trusted proxy peers, secret injection,
health routing, migration serialization, retention scheduling and backup recovery.
Official references: [Coolify build/deployment model](https://coolify.io/docs/core/build-deployment-model)
and [health checks](https://coolify.io/docs/applications/configuration/health-checks).
Their documented options do not establish that our future VPS is configured or tested.

## Continuous worker and Coolify secret delivery

The optional worker runs the same immutable image with command
`python -m app.knowledge_watch`. It requires GitHub HTTPS egress, PostgreSQL and
Neo4j writes, and authorized OpenAI embeddings when enabled. Its bare source cache
is temporary under writable `/tmp`; no additional persistent application volume is
required. The worker exposes no HTTP port. Disable the image's inherited API
HEALTHCHECK for this process (`docker run --no-healthcheck` locally); vps-ops must
verify the corresponding Coolify override rather than probing port 8000. Monitor
process liveness and the persisted successful `knowledge_watch.checked_at`
separately from corpus activation/freshness. A failed candidate can have healthy
source polling while answers remain temporarily unavailable.

Use one replica; an advisory lock refuses a second worker. Source polls
are 60 seconds and freshness expires after 90 seconds by default. Configure
`REQUIRE_FRESH_KNOWLEDGE=true` for production OpenAI. Do not put the polling task
inside the HTTP process. Startup does not create migrations or grant privileges.

Allow at least 60 seconds for worker termination. SIGTERM prevents further chunks
from being embedded and blocks activation; the current bounded operation finishes.
Git/embedding timeouts are 30/20 seconds respectively. The API's streaming grace
remains separate. vps-ops must verify restart/probe and shutdown behavior on Coolify.

Coolify is the initial secret store/delivery mechanism. Disable Build Variable for
runtime secrets; never build images with credentials. Protect the control plane
with restricted access and 2FA. Keep encrypted backups and the matching APP_KEY
outside this VPS, with a tested recovery procedure. No Infisical, Redis or external
secret SDK is required. Applications support runtime environment delivery, not
native _FILE loading. Missing values fail validation without returning their values.
Production remains unauthorized; none of these settings enable a deploy trigger.

OpenAI mode accepts only GPT-6 Luna and medium effort. Output/reasoning ceiling:
8192 tokens; emergency rendered-output bound: 40000 characters. Responses use
store=False; provider retention is still subject to the account's applicable policy.
Generation and embeddings share the approved USD 10 monthly ledger. No fallback
model/provider, automatic billed generation retry or external SaaS tracing. Private manual OTLP is optional; see the operational contract.

Frontend handoff: SSE v1 schema/examples remain unchanged. OpenAPI gains the public
knowledge/suggestions GET endpoint; import the complete committed snapshot before
claiming paired-contract release readiness. New safe failure codes are
provider_unavailable and knowledge_updating. Header behavior is no-store for private
API responses and no-store,no-transform for streams. Catalog absence/freshness failure
must not start a generation retry loop.


## Application-owned database tuning

Root `compose.yaml` is an isolated local/test specification, not the shared
production stack. It pins service images, binds development ports to loopback,
retains project-scoped volumes, prevents privilege escalation and rotates local
logs at 10 MiB × 3 per service. No fixed container names or production secrets.

| Service | Local ceiling | Application-specific settings |
| --- | --- | --- |
| PostgreSQL/pgvector | 512 MiB, 0.75 CPU, 128 PIDs, no extra swap | shared_buffers 128 MiB; work_mem 4 MiB; max_connections 50; shutdown grace 30 s |
| Neo4j Community | 1536 MiB, 1 CPU, 192 PIDs, no extra swap | initial/max heap 256 MiB; page cache 256 MiB; shutdown grace 60 s |

These are tested fixture ceilings, not reservations or a VPS capacity guarantee.
`work_mem` applies per operation; 50 connections is a bound, not a throughput
target. API pools are bounded at 8 application + 4 checkpoint connections per
process; workers, migrations and backoffice need separate capacity. Neo4j also
needs native/JVM memory beyond configured heap/cache. Let vps-ops measure the
combined workload and preserve OS, backup, proxy and other-project headroom.
Do not blindly impose read-only roots, arbitrary users or dropped database
capabilities: official image initialization and durable data permissions must work.

Validation: `uv run python -m scripts.validate_compose` checks the local resource,
log and loopback invariants and the retained production transfer reference. It
does not validate the actual Coolify server. See [dated local evidence and release
blockers](verification/runtime-2026-10-10.md). Production databases have private
networks and no public host ports; their canonical composition belongs to vps-ops.

Current patch and vulnerability evidence: [runtime security verification](verification/runtime-security-2026-10-10.md).


## Application-owned PostgreSQL artifact

Build: `docker build --platform linux/amd64 -f Dockerfile.postgres -t portfolio-assistant-postgres:local .`.
Root Compose is local/test only and builds this image; production composition stays
in vps-ops. Planned package name is ghcr.io/gonzalomartinperez/portfolio-assistant-postgres,
private unless separately authorized. No publication workflow has been activated
for this new artifact and no registry digest is claimed. vps-ops must consume an
authorized tested digest; local image IDs are not registry manifests.

The inherited entrypoint/docker command initializes a fresh cluster only when
PGDATA is empty, then execs postgres. It binds internal TCP 5432 and exposes no
production host port. UID/GID 999 needs ownership of the /var/lib/postgresql parent mount (PGDATA=/var/lib/postgresql/18/docker); an
existing volume is not automatically chowned. Mount only the reviewed data volume
and writable /tmp plus /var/run/postgresql (UID/GID 999, mode 3775). Read-only root,
dropped capabilities and no-new-privileges were tested. pg_isready checks server
acceptance, not application schema/corpus readiness; API /health/ready remains
the application readiness check. Allow at least the tested 30-second stop grace;
PostgreSQL's inherited signal/entrypoint owns database shutdown.

Fresh initialization requires POSTGRES_USER, POSTGRES_DB and secret POSTGRES_PASSWORD
or the official entrypoint's POSTGRES_PASSWORD_FILE mechanism, readable by UID 999.
Never use trust authentication. Deliver credentials privately through Coolify;
retain separate schema-owner and restricted API roles. Changing bootstrap variables
does not change credentials in an existing cluster. Runtime PostgreSQL options
include shared_buffers=128MB, work_mem=4MB and max_connections=50 in local tests;
these are measured-test settings/ceilings, not a VPS capacity promise.

Image replacement alone does not update SQL extension metadata in existing databases.
Before the API starts, the database owner must review and run ALTER EXTENSION vector
UPDATE TO '0.8.7' where needed, then verify extversion. This is separate from the
application's checksummed migrations; never edit applied migrations. Rehearse backup
and restore before replacing production database images. An old image is not a
guaranteed rollback after an extension/store upgrade. Default PostgreSQL stdout logs
are managed by vps-ops; do not enable parameter/statement logging for private chats.

[Database image evidence and unresolved findings](verification/database-images-2026-10-10.md)
are production assessment gates, not waivers. Publication approval, visibility,
compatible artifact selection and restoration remain external owner decisions.

The [vps-ops dispatch request](vps-ops-request.md) connects these application contracts to the separate operations owner without granting deployment authority.

Support and upgrade decisions: [supported-version policy](support-policy.md). Python3.14.8 remains the verified runtime; PostgreSQL18 uses a separate data volume.

## Private monitoring handoff (migration 006)

[Private observability](private-observability.md) defines the JSON/Prometheus read API
and bounded manual OTLP instrumentation. Runtime env requirements are in
[environment schema](environment.md). Keep `/internal/ops/*` unreachable through
the public proxy; only authenticated backoffice server and private Prometheus scrape
clients receive the runtime token. This is independent from visitor sessions/CSRF.

No extra public ports, filesystem persistence or migration controller are introduced.
SQL observations use existing PostgreSQL; grant runtime SELECT/INSERT after migration
006. Schedule retention with schema-owner credentials: seven-day phase retention,
30-day facts. Existing private pool/connection limits apply. An older API image rejects
the new migration history; rehearse paired rollback or restoration, never assume
reverting an image undoes schema changes.

OTLP HTTP export is disabled by default. If selected, allow private collector egress
on its configured port (typically 4318), with no unrestricted internet telemetry.
The collector, Prometheus, Grafana, persistent volumes/resources/access controls
and actual image versions belong exclusively to vps-ops. Prometheus 3.13 LTS is the
reviewed target; choose supported Grafana patches under its own support policy.
No monitoring stack is deployed by merging this repository.

SIGTERM closes active runs before draining observations and closing SDK/pools. Queue
drain is limited to two seconds; in-progress SQL writes are joined under short SQL
limits. SDK network shutdown remains best effort under underlying DNS/socket behavior.
Readiness checks verify schema/corpus and stores, not paid OpenAI service availability.
No model request runs on health checks or scrape requests.

Provider HTTPS uses verified TLS, no redirects, no inherited proxy/CA settings and
no automatic retries. Native SDK pool defaults are unchanged and are not a measured
VPS concurrency budget. All owned cleanup is attempted; failures remain visible.
Read [the transport handoff](verification/provider-transport-2026-10-17.md) before
changing egress, certificates or termination settings. No HTTP/2 dependency or
server protocol change is required for this increment.

Backoffice compatibility reference: `618aa914ced48bf08ba8d613537ecd28ef797d5e`. The
private v1 schema and synthetic example are in contracts/. Chat HTTP/SSE schemas
remain unchanged. Effective Coolify routing, exporter connectivity, dashboard
authentication and production monitoring remain deployment/paired verification gates.

The committed operational contract is available in develop via PR #47, merge
`8d411d76699c98e512f07127af371e2b6305fd57`. Local image verification and exact limits
are in [the dated operations report](verification/private-observability-2026-10-12.md).
Do not promote its local engine ID to a registry digest or production authorization.

## Optional official-documentation complement

`WEB_SEARCH_ENABLED` defaults to false. `WEB_SEARCH_TIMEOUT_SECONDS` defaults to 12
(1–15); `WEB_SEARCH_USD_PER_CALL` defaults to USD0.01 and must cover the reviewed fee.
These are runtime configuration, not credentials. Enabling also requires authorized
OpenAI mode and paid allowance. The existing backend-only OpenAI key is reused.
No new service, volume or migration is needed. See [bounded web policy](bounded-web-context.md)
for exact routing, privacy, cache, accounting and failure semantics. Production
activation remains separately authorized and vps-ops-owned.

## Shared runtime baseline

See [runtime-baseline.md](runtime-baseline.md) for the2026-10-13 shared cohort and image
acceptance. Actual committed locks and Dockerfiles supersede historical version/size samples;
no production publication, deployment or live OAuth/provider check is implied.

## Optional product analytics (not activated)

`PRODUCT_ANALYTICS_ENABLED=false` by default. Migration 007 and runtime grants are
additive; no new port, volume, collector or secret. The existing PostgreSQL holds
bounded anonymous event dedupe/daily aggregates. See [product analytics](product-analytics.md)
for quotas, provisional local retention and private route exclusion. The maintenance
job must continue expiry when collection is off; backup expiry/restore, lawful basis,
notice and production resource acceptance remain owner/ops gates.

## Neo4j immutable vendor refresh

The same-version5.26.32 candidate was rejected after deep scanning; runtime retains
the prior pin, which also has unresolved findings. Equal version labels do not mean
equal bytes or a repaired image. See [exact references, historical issues and release scan
procedure](verification/neo4j-vendor-refresh-2026-10-17.md). Normal API/PG CI alone
does not scan the complete Neo4j Java inventory. Manually dispatch Quality with
`verify_vendor_image=true` for the reviewed source and preserve the full scanner receipt
before release selection. A normal green dispatch or source tag is not this assessment.
Unresolved critical applicability, store recovery and actual VPS acceptance remain
release gates; no clean-stack or production-approval claim is made.
## Current release hold and feedback read

The [dated Neo4j security assessment](verification/neo4j-release-blocker-2026-10-17.md)
blocks production selection; ordinary API/PG CI is not vendor Java acceptance.
`FEEDBACK_OVERVIEW_ENABLED=false` gates the optional private current-rating read
using existing OPS_READ_TOKEN. No migration, service or new volume is required.
See [privacy and feedback](feedback-and-improvement.md); no raw conversations or
automatic learning are exposed. Original history retention is unchanged.

## Optional manual evaluation export (not part of API deployment)

The [synthetic-summary CLI](synthetic-evaluation-export.md) is a separately invoked
development operator tool. It needs no port, migration, writable application path,
daemon or backoffice feature. The API never creates its client. Do not provision
`EVALUATION_LANGSMITH_API_KEY` in normal API/worker/Coolify environments or enable
global tracing. A separately approved manual export uses that server-side process
environment credential and the fixed HTTPS LangSmith endpoint/project documented
there. No account or external export has been activated or tested. Existing OTLP/OPS
runtime delivery remains unchanged; public/SSE/private schemas are unchanged.

## Query-index migration and rollback

Migration 008 adds `spend_ledger_created_at`, a normal B-tree used by the unchanged
UTC monthly cost predicate. It changes no row/ownership, quota, reservation or
idempotency semantics. The transactional runner deliberately uses normal index
creation, not `CONCURRENTLY`: schedule a reviewed maintenance window for writes and
measure larger datasets before production. Existing statement/lock timeouts can
abort the migration safely; do not disable them to force completion.

The knowledge writer also creates the idempotent Neo4j range index
`entity_version_normalized(version, normalized)` after the projection transaction,
then waits at most 30 seconds for indexes before activating knowledge. It uses
existing Neo4j schema-writing privileges. No new PostgreSQL DDL grants are introduced;
`deploy/runtime-grants.sql` governs PostgreSQL only. Neo4j Community credentials
remain privileged: fixed read templates are application behavior, not database-enforced
reader authorization. Keep the graph isolated and limited to the approved public,
rebuildable projection; never colocate conversations or other private/project data.
See [the graph authorization boundary](graph-retrieval.md#authorization-boundary).
No new container, port, extension, plugin, environment variable or secret is required.
The application retains its two-second graph-read limit and exact vector search.

After applying 008, a pre-008 checkout fails strict migration-history readiness.
Do not roll back to the immutable v1.1.0 image expecting it to start. A forward-fix
or prepared compatible rollback image must retain migration 008 and its checksum;
application rollback does not remove the index or reverse the database history.
Restore/recovery procedures remain vps-ops-owned. Read the
[measured query evidence](verification/database-queries-2026-10-17.md) before release
selection; synthetic local measurements are not VPS capacity acceptance.

## Software licensing files

The application source uses MIT. `/app/LICENSE` and `/app/THIRD_PARTY_NOTICES.md`
are shipped read-only and checked by the existing non-root container smoke.
The OCI MIT label identifies this application's source; dependencies/base images
keep their own packaged licenses, and personal/career content is outside that grant.
No package publication, production approval or change to immutable tags follows.
