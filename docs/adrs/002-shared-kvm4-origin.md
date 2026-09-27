# ADR 002: shared KVM 4 VPS and one assistant origin

Accepted by owner 2026-09-27; supersedes prior hosting-topology suggestions.
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

The committed portfolio at `e411c0a775b16fd7de962774d875e47191f96b09` has a native
assistant panel making credentialed API calls, plus a standalone-chat link. It is
not framed. Allow exactly the assistant origin and `https://gonzalomartinperez.com`;
add `www` only if a real consumer is verified. Parent-domain sharing does not remove
CORS or CSRF obligations. The host-only Secure HttpOnly SameSite=Lax cookie lives
on the assistant hostname; both HTTPS origins are same-site but cross-origin.
No Domain cookie or wildcard credentialed CORS is permitted.

## Operations and cost

`deploy/compose.yaml` is the single shared stack specification in this API repo.
The frontend owner supplies a committed image/configuration handoff; do not build
or maintain a competing frontend Dockerfile here. Databases use a private internal
network and persistent project-scoped volumes, with no host ports. Only the proxy
publishes traffic. Additional VPS projects need their own networks/volumes and
routes in the same chosen proxy. Coolify is optional management, not a selected
second proxy. If selected, translate these routing controls into its sole proxy
and omit the bundled proxy profile.

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
