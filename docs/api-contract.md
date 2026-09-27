# Public API and SSE v1

Authority: this repository. Machine artifacts: [OpenAPI](../contracts/openapi.json),
[SSE JSON Schema](../contracts/sse.schema.json), and [stream examples](../contracts/sse.examples.json).
Regenerate deterministically with `uv run python -m contracts.export`. CI rejects
drift. Schema version remains `1`; the SSE schema now documents existing payloads
more precisely. Frontend consumers import a committed snapshot themselves.

## Session and browser requests

Use `credentials: 'include'`. Bootstrap `POST /api/v1/session` with JSON `{}`,
`Origin: http://localhost:3000` (or `http://localhost:3001`) and
`X-Session-Bootstrap: 1`. The response sets the anonymous HttpOnly cookie and returns:

```json
{"csrf_token":"<opaque token>","expires_at":"2026-10-04T12:00:00Z","retention_days":7}
```

`GET /api/v1/session` restores CSRF/expiry. Mutations require the exact trusted
Origin and `X-CSRF-Token`. The token is session-specific. The cookie is
`assistant_session_dev` locally, `__Host-assistant_session` in production, host-only,
SameSite=Lax and Secure in production. Use `localhost` consistently in browser URLs;
`127.0.0.1` is a different cookie host. CORS exposes `X-Run-ID` and `X-Request-ID`.

## Operations

| Method/path | Behavior |
| --- | --- |
| POST/GET/DELETE `/api/v1/session` | Bootstrap, restore, delete anonymous ownership |
| POST/GET `/api/v1/conversations` | Create/list owned conversations |
| PATCH/DELETE `/api/v1/conversations/{id}` | Rename/delete owned conversation |
| GET `/api/v1/conversations/{id}/messages` | Newest-first history and cursor |
| POST `/api/v1/conversations/{id}/messages/stream` | Create a bounded run and stream SSE |
| GET `/api/v1/runs/{id}` | Read run state after interruption/reconnect |
| POST `/api/v1/runs/{id}/cancel` | Idempotently cancel a live owned run |
| POST `/api/v1/messages/{id}/feedback` | Up/down feedback on owned assistant message |
| GET `/health/live` | Process responds; no dependency I/O |
| GET `/health/ready` | Database schema, active corpus and graph connectivity |

A stream request body is `{"content":"What is Filomena?","locale":"en"}`;
Spanish uses `"locale":"es"`. Supply an `Idempotency-Key` of 8–128 characters.
Duplicates return 409 (`run_already_exists`, or `idempotency_conflict` for a changed
body). Streams are not replayed. Foreign objects return 404, missing/expired session
401, CSRF/origin failures 403. Input errors use 400/422; rate, storage and concurrency
bounds use 429; dependency availability uses 503. Errors retain
`{"code":"...","message":"...","request_id":"..."}`. See OpenAPI for exact shapes.

## Stream order

Each frame contains `event: <name>` followed by `data: <JSON>` and a blank line.
The envelope has `type`, `schema_version`, UUID run/conversation IDs, monotonically
increasing `sequence` starting at zero, UTC `timestamp` and a typed `payload`.

| Event | Payload | Order |
| --- | --- | --- |
| `run.started` | `{"state":"running"}` | First after successful claim |
| `run.status` | `{"phase":"evidence_found","sources":2}` | Before generation |
| `message.delta` | `{"text":"incremental text"}` | Zero or more |
| `message.completed` | Message ID, full content and citations | Only after atomic persistence |
| `run.completed` | `{"state":"completed"}` | Successful terminal |
| `run.failed` | `{"code":"generation_failed"}` or budget code | Failure terminal |
| `run.cancelled` | `{}` | Cancellation terminal; may be first if claim was cancelled |

Exactly one terminal is sent when delivery is possible. Disconnects cannot receive
a terminal frame. Partial text is transient, not a saved assistant message. Storage
failure may delay persisted interruption until lease recovery. Cancel is checked
while the provider is silent. Requests can time out; clients should keep the run ID
and query state rather than implicitly resubmitting paid work.

Citations contain chunk identity, label, public URL, source kind, immutable source
commit, path and line range. They identify supplied evidence; they do not prove that
every live-model statement is entailed. Fixture output is literal excerpts or a
bilingual abstention. No hidden reasoning, graph state or internal tool payloads
are public progress events. Disable proxy buffering/cache for SSE.
