# API runtime handoff to vps-ops

Status: application contract, not deployment authorization. Coolify is selected
for the future Hostinger KVM 4 VPS and managed only through private vps-ops.
The portfolio remains on Business. No Coolify installation or production test has
been performed here. The commit containing this document identifies its revision.

## Artifact and runtime

Build locally: `docker build --platform linux/amd64 -t portfolio-assistant-api:local .`.
CI currently verifies Linux amd64 only. The candidate publisher prepares
`ghcr.io/gonzalomartinperez/portfolio-assistant-api:<full-source-SHA>` and records
its immutable `@sha256:` digest. Publication is not yet authorized; confirm package
visibility separately, and provision pull access in vps-ops if private. Consume
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

Tested services: PostgreSQL 17 with pgvector 0.8.1; Neo4j 5.26.17 Community.
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

**Rollback limitation:** readiness rejects unknown applied migrations. Older images
may therefore be incompatible after an upgrade even when tables are additive.
Review each image/schema pair explicitly; never assume overlapping old/new versions
or automatic down migrations. Backups and restore into a separate database require
a separately tested recovery procedure.

## Health, routing and streams

- `GET /health/live`: process response, not dependency readiness.
- `GET /health/ready`: schema/checksum, active public corpus and graph connectivity;
  use as the traffic admission probe. No paid model call.
- Suggested container probe: `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5)"`.
  Initial settings: interval 20s, timeout 8s, retries 3, start period 30s; verify on VPS.

Preserve `/api/v1/...` verbatim. FastAPI `root_path` is empty: never strip/add `/api`.
Route `/` to frontend; docs `/docs`, `/redoc`, `/openapi.json` and `/health/*` require
explicit API routing or restricted administrative access. The API contract artifacts
remain authoritative. vps-ops must verify the exact Coolify routing configuration.

Disable SSE buffering and caching; propagate disconnects. Heartbeat comments occur
after 15 seconds of silence. Proxy read/send timeout must exceed maximum run bound
120 seconds (reference uses 135). Body limit reference is 32 KiB; proxy rejection
is 413. Preserve `no-store` for sessions/conversations/streams. Overwrite untrusted
forwarding headers and configure exact trusted peers. TLS/security headers and any
Cloudflare layer require separate end-to-end verification.

Host-only Secure HttpOnly SameSite=Lax `__Host-assistant_session` has no Domain
attribute. Mutations still require allowed Origin and CSRF token. Allow exactly
`https://assistant.gonzalomartinperez.com` and `https://gonzalomartinperez.com`:
the existing portfolio panel calls the API cross-origin and is not an iframe.
No wildcard credentialed CORS. Standalone browser requests should use relative `/api`.

## Evidence and verification

Local/CI image and Nginx fixture tests are recorded in IMPLEMENTATION_STATUS.md and
[CI](ci.md); they are not Coolify tests. Historical local idle stack measurement
~874 MiB included web and both databases; not a VPS guarantee. Previous proposed
resource ceilings are retained only as transfer inputs in deployment.md. vps-ops
owns final measurement/allocation. JSON stdout logs include correlation, latency,
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
