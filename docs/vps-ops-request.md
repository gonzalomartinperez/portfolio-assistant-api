# Dispatch request for the vps-ops owner

Use this as task context, not production authorization. The application repositories
remain public engineering projects; production inventory, secrets references and
operations belong in private vps-ops. No real secret should enter either repository.

Prepare the coordinated Coolify deployment of portfolio-assistant-api and
portfolio-assistant-backoffice on the future Hostinger KVM 4 VPS. The actual
portfolio stays on Hostinger Business, its native assistant remains disabled, and
no launcher, site, DNS, infrastructure or production rollout is authorized by this
handoff. Inspect existing vps-ops instructions and preserve all existing work.
Do not install a competing proxy/controller or independently edit application code.

Read the API's committed docs/deployment-contract.md, docs/environment.md,
docs/frontend-handoff.md and the dated runtime/database verification reports.
Read the backoffice owner's committed deployment contract at its identified release
revision; its previously inspected baseline was 618aa914ced48bf08ba8d613537ecd28ef797d5e.
Reconcile newer committed handoffs at a meaningful milestone. Do not depend on
mutable working trees, private career-ops files or historical iframe assumptions.
The API v1 context contract originated at 61da393520014ed2c8b1f8a0635b3b4e615f9e53;
subsequent runtime patches preserve those wire artifacts. Record selected source
revisions and actual tested image digests in one compatibility manifest.

## Artifact selection and routing

Applications own their source, Dockerfiles, tests and runtime contracts. Consume
prebuilt tested immutable image digests after separately authorized publication;
no source rebuild on the VPS as the normal release path. API image publication
preparation exists; no registry digest or publication approval is supplied here.
A separate application-owned Dockerfile.postgres now builds patched PostgreSQL
17.11 / pgvector 0.8.7. Its publication and package visibility still require
separate authorization. Local image IDs in reports are not registry manifests.

Manage Coolify and its effective proxy through vps-ops. API binds internal 8000;
backoffice binds its documented internal 3000. PostgreSQL 5432 and Neo4j Bolt 7687
remain private, with no public database/admin ports. Proposed assistant origin is
https://assistant.gonzalomartinperez.com; preserve /api/v1 paths end-to-end, avoiding
prefix stripping or /api/api. Select the backoffice's authenticated route/origin
only after reconciling its contract; the native portfolio chat is a separate-origin
consumer. Do not restore a production /embed mode or enable the native rollout.

Verify effective TLS/security headers, credentialed CORS for only required exact
portfolio origins, host-scoped secure cookies and unchanged Origin/CSRF enforcement.
A shared parent domain is not same-origin. Trust only identified proxy peers;
Uvicorn does not rewrite forwarded headers. Streaming goes directly to FastAPI,
with buffering/cache disabled, documented heartbeats/timeouts and tested client
cancellation. Evaluate Cloudflare as an additional layer only if actually selected.

## Provisioning and data lifecycle

Provision secrets privately via Coolify's supported runtime delivery. Follow typed
application configuration, separate schema-owner/runtime/worker grants and the
backoffice's auth allowlist. Never expose provider/admin secrets in frontend builds,
URLs, image layers, CI artifacts or logs. PostgreSQL runs UID/GID 999 and skips
root ownership repair: prepare owned PGDATA and socket tmpfs deliberately. Existing
bootstrap environment changes do not rotate existing cluster passwords.

Coordinate checksummed API migrations 001–005 and checkpoint setup before readiness;
these are not one complete atomic operation. Review explicit vector extension
upgrades independently of application migrations. Schedule approved public-corpus
sync and retention commands from the exact selected image. Only approved published
portfolio content enters knowledge; visitor theme/path metadata is untrusted.
Keep fixture mode until separate model/embedding usage authorization. Authorized
production model policy is OpenAI-only GPT-6 Luna, medium, no provider fallback,
with the configured shared budget. The small isolated experiment does not authorize
additional production calls or a full paid question-bank run.

Create encrypted off-server backups and demonstrate restoration into isolated
stores before production selection. Neo4j Community and PostgreSQL recovery must
follow their actual supported tools; do not promise automatic migration reversal,
image-only database rollback, high availability or zero downtime. Preserve a known
compatible image/schema/corpus combination and rehearse application rollback and
database recovery as separate procedures.

## Security, resources and acceptance

The API scan still has unresolved OS high findings. Patched PostgreSQL removed all
fixable findings in the recorded scan but retains three critical findings without
listed fixes. Neo4j's full OS/Java scan retains an unfixed headers critical finding
and fixable vendor Jackson highs. Assess runtime applicability and supported vendor
patches; never silently suppress findings or replace vendor jars. A passing
application CI remediation gate is not production security approval. Rescan selected
release digests using current advisory data and record unresolved release blockers.

Local database ceilings are PostgreSQL 512 MiB / 0.75 CPU and Neo4j 1536 MiB / 1 CPU;
they are fixture settings, not measured VPS guarantees. Allocate shared capacity
for the OS, Coolify/proxy, backups and other projects after measurement. Keep project
names, networks, volumes and logs isolated. Bound log/disk retention and verify
startup, resource pressure and shutdown on the actual VPS; avoid aggressive JVM
or connection increases without observed demand. No external tracing is enabled
in the tested API. Do not add monitoring vendors or analytics without a separate
request; actual backoffice metrics need a committed private operations contract,
which is not yet implemented by this API. Fixture dashboards are not real metrics.

Prepare an approval-gated, serialized release procedure selecting tested digests,
coordinating reviewed migrations, checking API readiness and authorized chat/SSE,
and restoring the previous compatible application artifact on failure. Keep
production execution, deployment webhooks and automatic triggers disabled. First
verify the stack locally with isolated safe fixture services and retained evidence.
Do not stop unrelated containers or remove shared volumes. Report exact revisions,
image digests, effective headers/routes, backup/restore evidence, resource results
and outstanding owner decisions before requesting production authorization.
