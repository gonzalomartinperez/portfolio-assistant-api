# Frontend integration handoff

Immutable API snapshot: **`4602abe7c69487b37fab54eed173531011d47b82`**.
Contract version **1**, API version **1.0.0**. Import from this committed revision:

- `contracts/openapi.json` — unchanged public HTTP surface.
- `contracts/sse.schema.json` — discriminated event payloads for the existing seven events.
- `contracts/sse.examples.json` — success/abstention, failure and cancellation.
- `contracts/manifest.json` — deterministic artifact hashes.

The frontend owner imports this snapshot and regenerates types in its own PR.
No frontend working-tree files are dependencies of this handoff. Requests/events,
headers, session flow and cancellation are documented in [API contract](api-contract.md).
Start the fixture API with [local setup](local-development.md); it uses no model key.

## Compatibility

Existing `/api/v1/...` paths, ownership, CSRF, cookies, idempotency conflict behavior,
SSE names/ordering and history semantics remain. SSE payload validation is more
precise, with no renamed events. New abuse limits may reject oversized bodies,
conversations/history or expired execution; use the existing public error shape.
On failure/disconnect do not automatically regenerate. Keep `X-Run-ID`, query run
state and offer an explicit user retry. Only `message.completed` is durable output.

Use credentialed requests, exact trusted Origin and the current session's CSRF
header on every mutation. Bootstrap requires JSON and `X-Session-Bootstrap: 1`.
The default local browser origins are localhost ports 3000/3001. The server uses a
host-only HttpOnly SameSite=Lax cookie, Secure with `__Host-` naming in production.

## Deployment coordination request

The decided target is the future shared Hostinger KVM 4 VPS, proposed origin
`https://assistant.gonzalomartinperez.com`. The single reverse proxy sends `/` to
Next.js and **preserves** `/api/*` when routing directly to FastAPI. FastAPI has
empty `root_path`; do not prepend another `/api` or put SSE through a Next.js proxy.
The frontend should publish its committed image handoff with relative `/api/v1/...`
requests (empty public API origin), image digest, frontend commit, build-time public
configuration, writable paths and health endpoint. The API repository owns the
shared deployment specification. No DNS/deployment is authorized.

The portfolio's committed integration at `e411c0a775b16fd7de962774d875e47191f96b09`
contains a native panel that calls the API directly and a link to the standalone
assistant. It is not an iframe. Its production build needs the assistant HTTPS
origin for both public URL variables. Keep its exact `https://gonzalomartinperez.com`
origin allowlisted for credentialed API calls; a shared parent domain does not
remove CORS/CSRF requirements. No portfolio change is made here.

Frontend commit `c374aeb95484904ebdbe731a5659dc4b145d6eaf` now publishes its
standalone image/configuration handoff. The shared stack includes its UID 1000
32 MiB cache tmpfs. Its immutable registry digest and combined release remain
pending. Canonical edge limits here are 32 KiB bodies and 135-second read/send
timeouts; API comments provide 15-second heartbeats. The frontend owner should
reconcile its earlier 16 KiB/no-heartbeat proxy notes with this API-owned stack. Fixture excerpts
and hash embeddings are deterministic development behavior, not live-model quality.

Local HTTP full-stack verification passed against frontend commit `c374aeb95484904ebdbe731a5659dc4b145d6eaf`: root, API/docs, CORS/CSRF, incremental deltas and disconnect interruption. Its imported contract bytes match this API snapshot. Browser/TLS and registry digest release checks remain separate. See [diagnostic summary](verification/backend-rc.json).

## Conversational increment · source revision 6b1e65f2406ba5ddf21d15c56c34ccf672d90bbb

The v1 HTTP/OpenAPI and seven SSE event schemas remain byte-compatible; no frontend
type regeneration is required for a wire change in this increment. Continue using
the committed artifact paths and examples above. Server-side history now supplies
bounded context from the same owned conversation. Send follow-ups to the existing
conversation ID; do not resend full history or place visitor statements in citations.

Existing validated citation references remain the optional presentation enhancement;
no arbitrary action/HTML/URL schema was added. Text is complete without navigation.
Fixture output is readable quoted source prose, not a live-model quality claim.
Shortening is deterministic; nuanced role-fit/depth/personality need separately
authorized live evaluation. Full partial-stream/cancel/failure semantics are unchanged.

Production is coordinated exclusively by private vps-ops using Coolify. The API
[deployment contract](deployment-contract.md) preserves `/api/v1` paths with empty
root_path. This revision does not authorize image publication or deployment.
