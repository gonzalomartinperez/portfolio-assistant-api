# Frontend integration handoff

Current immutable API snapshot: **`61da393520014ed2c8b1f8a0635b3b4e615f9e53`**.
Contract version **1**, API version **1.0.0**. Import from this committed revision:

- `contracts/openapi.json` — compatible v1 HTTP surface plus the public starter catalog.
- `contracts/sse.schema.json` — discriminated event payloads for the existing seven events.
- `contracts/sse.examples.json` — success/abstention, failure and cancellation.
- `contracts/manifest.json` — deterministic artifact hashes.

Earlier snapshot `5742961` remains historical compatibility evidence, not the
snapshot for importing the new catalog. The 2026-10-04 audit observed frontend
develop `aed8ea710c8b847ddc9066aaef5ce48d3793b494` still pinned to API `6b1e65f`;
new catalog/error-state adoption and paired browser verification remain pending.
See [A3 closure criteria](live-evaluation-readiness.md#findings-and-closure-criteria).

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
configuration, writable paths and health endpoint. Private vps-ops owns production
composition and Coolify execution. This repository supplies the API runtime contract.
No DNS/deployment is authorized.

Actual portfolio integration is deferred. The consolidated mandate supersedes the
previous direct-panel integration plan; see the embedded-experience contract below.
No portfolio or frontend working-tree change is part of this handoff.

Frontend commit `c374aeb95484904ebdbe731a5659dc4b145d6eaf` now publishes its
standalone image/configuration handoff. The retained transfer template includes its UID 1000
32 MiB cache tmpfs. Its immutable registry digest and combined release remain
pending. Required reference edge limits are 32 KiB bodies and 135-second read/send
timeouts; API comments provide 15-second heartbeats. The frontend owner should
reconcile its earlier 16 KiB/no-heartbeat proxy notes with the runtime contract;
vps-ops implements and verifies the Coolify proxy. Fixture excerpts
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

## Embedded-experience contract

The primary UI is frontend `/embed`; `/` is a secondary testing/demo surface.
Both use same-origin relative `/api/v1/...` through the vps-ops-owned proxy, which
preserves the prefix. A parent iframe host neither receives the session credential
nor needs API CORS permission. Keep the assistant origin as the target allowlist;
legacy direct clients require their own explicit configuration and review.

Minimize/reopen should keep the iframe/controller mounted and reuse the session and
conversation history. A hidden mounted UI may finish its already authorized stream;
minimize is not delete, cancel or regenerate. Explicit stop or transport teardown
still cancels upstream work. Partial text is not durable until `message.completed`.
After a disconnect, recover existing history and run status, never automatically
retry generation. Session expiry/deletion keeps
its v1 semantics. Cross-tab transfer is not a release requirement.

Frontend/vps-ops must set exact allowed frame ancestors for `/embed` and test the
planned HTTPS parent/assistant combination. API CORS does not authorize framing.
Host-scoped Secure HttpOnly SameSite=Lax cookies remain unchanged. Unrelated-site
embedding is unsupported; do not silently switch to Domain cookies or SameSite=None.
Browser restrictions still require real verification. References: [cookie scope and
SameSite](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie)
and [frame ancestors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors).

Committed frontend reviewed: `a9a85bbf33e5ccbf8b81740b0efeb718490bd97e`.
Its contract source pins API `6b1e65f2406ba5ddf21d15c56c34ccf672d90bbb`; all three
HTTP/SSE artifacts were compared byte-for-byte and remain identical to the snapshot
above. Its committed embed protocol keeps the frame mounted during minimize and
uses exact parent-origin/source validation. It requires no API wire change.
The frontend's protocol handoff still labels browser verification in progress;
this backend does not claim that its iframe tests passed. Its older deployment
paragraph about direct portfolio API access also needs reconciliation by its owner
with the new embed handoff. Mutable sibling files were not integration evidence.

## Continuity increment · source revision 57429618cf487b78842dd460411a72da45728ba0

Named-example questions can switch subjects without inheriting the previous
employer; subsequent references retain the new topic and latest visitor refinement.
Role-fit wording no longer becomes an employer filter merely because it contains
"for". Fixture attribution excludes visible neighboring employer records. These
are backend behavior changes, not new request fields or SSE events. Existing
consumers and persisted conversations need no migration or type regeneration.

## Current-knowledge increment

This increment retains SSE v1 event names and payloads. OpenAPI adds
`GET /api/v1/knowledge/suggestions?locale=en|es` with corpus_version, source_commit
and bilingual section-backed items. The web owner must import a committed snapshot,
regenerate types and validate the catalog payload; do not read this working tree.
The endpoint is public and does not create a session or charge model use.

Handle `knowledge_updating` as a recoverable availability state and
`provider_unavailable` as an OpenAI outage. Neither permits automatic paid generation
retry. Existing clients still receive the v1 run.failed envelope and can use their
safe generic unknown-code behavior until localization is added. Session/cookie/CSRF,
run ownership, cancellation and source record shapes are retained. Cited real answers
now attach only the supplied references actually used as [1]…[5]. Fixture behavior
remains separately identified. Real-model citation support requires paid evaluation.

The source public projection and personal facts need the portfolio-owner handoff
in knowledge-sync.md. This repository does not implement the portfolio launcher,
CSP, frontend preferences or production deployment.


## Native portfolio presentation context · 2026-10-10

This current native integration supersedes the historical iframe deployment sections
above. The portfolio owns the native UI and keeps it disabled; the renamed
portfolio-assistant-backoffice owns the authenticated administration surface.
The runtime contract defines CORS/proxy requirements; no host source was changed.


Contract implementation: `61da393520014ed2c8b1f8a0635b3b4e615f9e53`.
`SendMessage.context` is optional; omission or JSON null preserves existing clients
and the legacy idempotency fingerprint. `locale` remains top-level `en`/`es`.
When present, all four fields are required and extra keys are rejected:

```json
{
  "content": "What is his experience?",
  "locale": "en",
  "context": {
    "theme": "dark",
    "opened_path": "/work",
    "current_path": "/about",
    "presentation": "compact"
  }
}
```

Theme: `dark`/`light`; presentation: `compact`/`expanded`/`page`.
Paths are exact values: `/`, `/about`, `/work`, `/work/filomena`, `/education`,
`/cv`, `/contact`, `/stack`, `/assistant`, and their `/es` equivalents (`/es`
for the home page). Assistant pages are supported conditional public routes;
accepting them as metadata does not enable the rollout. The allowlist references
portfolio commit `ccd4dd3b0a7d222b2fed384578cc847b7dddd93b`.
Queries, fragments, absolute/protocol-relative URLs, encoding tricks, traversal,
trailing slashes and arbitrary project slugs return the existing safe HTTP 422.
Future public routes require an explicit additive catalog update.

The HTTP adapter maps to a framework-free immutable `PresentationContext`;
application/LangGraph transport it separately from evidence and history. The
provider receives it under `untrusted_presentation_context` in user data, never
in developer instructions or retrieval evidence. It cannot change the language
policy, authorization, source provenance or system instructions. Fixture answers
ignore these hints; real answer quality is not guaranteed by prompt separation.
No context fields are returned in SSE/history or operational logs. Checkpoint
state can contain the bounded metadata and follows existing retention/deletion.

The complete request, including non-null context, binds the idempotency key;
changing context with the same key returns 409 and never starts another generation.
Paths are visitor claims, not proof that the host visited a page. Do not add
credentials, full URLs, transcripts or private parameters to the object.

Import OpenAPI and its regenerated manifest from the implementation SHA above;
SSE schemas/examples are unchanged. Generate TypeScript in the frontend's existing
isolated `openapi-typescript` toolchain. A local generated declaration was checked
with generator 7.13.0; API Python models remain the runtime validator, not generated
TypeScript. Request examples: [send-message.examples.json](../contracts/send-message.examples.json).

Verification: strict mypy; all 235 then-current tests with isolated PostgreSQL/
pgvector and Neo4j; 38 new offline validation/propagation cases plus HTTP integration
covering omission, valid context, rejection before provider calls, idempotency and
no SSE/history leakage. A subsequent example/fingerprint test also passed. No
paid calls were needed for this contract change; no deployment/activation occurred.
