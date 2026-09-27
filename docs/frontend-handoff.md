# Frontend integration handoff

Immutable API snapshot: **`94408ab4b59297e93e2574320b3049ee2f5d4f2e`**.
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

The frontend currently has ongoing uncommitted work; its new image/configuration
handoff is therefore a pending cross-repository integration gate. Fixture excerpts
and hash embeddings are deterministic development behavior, not live-model quality.
