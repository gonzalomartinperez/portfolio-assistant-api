# ADR 002: shared KVM 4 VPS and one assistant origin

Accepted by owner 2026-09-27; production ownership superseded by ADR 003; supersedes prior hosting-topology suggestions.
Both assistant web and API run on the future Hostinger KVM 4 VPS. The portfolio
remains on Hostinger Business; managed Node.js slots are reserved for other work.
Hostnames here are planning targets, not DNS or deployment authorization.

## Routing and trust

Proposed origin: `https://assistant.gonzalomartinperez.com`. One shared reverse
proxy serves `/` from the frontend and forwards `/api/*` directly to FastAPI,
**preserving the full URI**. Nginx `proxy_pass http://api:8000` has no URI suffix;
FastAPI `root_path` stays empty. There is no `/api/api`, Next.js API proxy, or
prefix stripping. `/docs`, `/redoc`, `/openapi.json` and `/health/*` are explicitly
routed to the API so generated documentation works without changing v1 paths.

The consolidated product mandate supersedes the earlier native portfolio-panel
integration plan. `/embed` is the primary frontend, `/` the secondary demo; both
call relative `/api` on the assistant origin. Actual portfolio integration is
deferred. The future parent iframe host does not require API CORS permission.
Default the deployment allowlist to the assistant origin alone; existing explicitly
configured consumers remain supported. Frontend/vps-ops own exact `/embed` framing
permissions and browser verification. Host-only Secure HttpOnly SameSite=Lax cookies,
CSRF and explicit Origin checks remain mandatory. No Domain cookie or wildcard
credentialed CORS is permitted. See the current frontend/runtime handoffs; frozen
Nginx global anti-framing headers are not a production `/embed` specification.

## Operations and cost

Production composition, networks, volumes, proxy and release orchestration belong
to private vps-ops. Coolify is the selected management platform. The previous
`deploy/compose.yaml` is retained only as a transfer reference and local verification
input. ADR 003 records the ownership transition; do not activate a competing proxy.

Initial assistant memory ceilings total about 4.4 GiB (API 768 MiB, web 512 MiB,
PostgreSQL 1 GiB, Neo4j 2 GiB, proxy 128 MiB). These are initial limits, not measured
capacity needs. Retain at least half of installed RAM for OS, backups, proxy peaks
and other projects until representative load proves a different allocation safe.
Measure CPU/RAM/disk/connection and stream latency before sizing other workloads.
No high availability or zero-downtime promise is made for one VPS.

## Release gates

Local tests validate exact proxy paths, CORS/CSRF, cookie behavior, unbuffered SSE,
client cancellation and container shutdown. Production still requires explicit
combined-release approval, compatible web/API digests, restore drill, DNS/TLS,
proxy forwarded-peer inventory and representative load. Cloudflare is an optional
extra layer and needs its own streaming/timeout test if enabled. There is no
active deployment workflow or automatic `develop` deployment.

## Sources

- https://nginx.org/en/docs/http/ngx_http_proxy_module.html — URI preservation, buffering and read timeout semantics.
- https://docs.docker.com/reference/compose-file/services/ — service limits, health checks and hardening.
