# Private observability and backoffice contract

This application implements first-party operational measurements. Export to a private
OpenTelemetry collector is optional and disabled by default. No production monitoring
stack or deployment is created here. LangSmith and automatic LangChain tracing remain
disabled. vps-ops owns collector, Prometheus, Grafana, storage, access and Coolify.

## Data boundary

Only claimed executions are observed. A separate random 128-bit trace ID is unrelated
to run/session/conversation IDs. Measurements include outcome, total duration, time to
first server fragment, bounded named phases and an allowlisted public error code.
Questions, responses, system prompts, documents, source text, credentials, client IPs,
user IDs and full LangGraph state are excluded from the observation model.

All claimed executions enqueue without awaiting storage or network export. The queue
holds at most 128 entries. Overflow, export exceptions and failed writes increment a
private dropped-observations gauge. Consequently totals are observed executions, not
an exact financial or audit ledger. Collection failures never retry generation.

Manual OTLP spans cover language selection, vector retrieval, graph retrieval,
generation and finalization. They do not instrument every token or export SDK arguments.
An explicit Resource contains only service name and source revision. Incoming trace
parents are not adopted. Sampling defaults to 10%; fixtures can select 100%.

SDK requests use separate sessions with environment proxy/credential discovery and
redirects disabled. Other vendor `OTEL_*` environment hooks are rejected at exporter
initialization, except the two supported application settings. Export payloads are
bounded to 256,000 bytes, SDK queues to 128 and requests to a one-second timeout.
Timeouts are best effort: DNS and operating-system networking can exceed a Requests
socket timeout. SDK diagnostics use fixed public messages rather than exporter
responses or exception details. Production egress restrictions remain a vps-ops gate.

## Server-to-server endpoints

- `GET /internal/ops/v1/status`: versioned JSON for the backoffice.
- `GET /internal/ops/v1/metrics`: Prometheus exposition from the same verified snapshot.

Both require `Authorization: Bearer <OPS_READ_TOKEN>`; configure a random URL-safe
32–256-character value through runtime secret delivery. Never expose it in browser
JavaScript. Unconfigured access returns 503, invalid/missing credentials return 401,
and dependency/validation failure returns a safe 503. Responses, including failures,
are `Cache-Control: no-store, no-transform`. These routes are absent from public
OpenAPI and must be denied by the public proxy. No administration/write API is added.

[Schema](../contracts/operations.schema.json) and
[example](../contracts/operations.example.json) define version 1. Unknown fields,
non-finite/negative values, inconsistent totals and unsupported phase names are
rejected. Snapshots have at most 100 traces and 16 phases per trace. A shared four-second
HTTP deadline fits the backoffice's five-second timeout; timed-out synchronous probes
may finish afterward under their adapter limits.

The schema matches the committed backoffice proposal at
`618aa914ced48bf08ba8d613537ecd28ef797d5e`. Its authenticated Next.js route fetches
this endpoint server-side; browser OAuth/UI verification is still independent.
Do not assume fixture charts or this backend implementation verify the deployed pair.

## Meaning of dashboard values

- Availability verifies application schema, active corpus and database/graph connectivity.
  It does **not** probe a paid OpenAI generation or certify live provider availability.
- Knowledge freshness compares the latest public source observation with the active
  index and the configured freshness deadline. Fixture databases without a source-watch
  observation are accurately reported stale/degraded.
- Counts and p50/p95 first-fragment latency use a rolling 30-day observed-execution window.
  First fragment is a server measurement, not browser rendering or field Web Vitals.
- Usage uses the current UTC month. Settled/reserved USD values are configured estimates,
  not an OpenAI invoice. The pricing revision hashes the actual configured price tuple.
- Token counts sum known settled usage. Historical ledger rows with NULL token counts
  cannot be reconstructed and are excluded; zero is not proof of complete historical coverage.
- Sampled trace drilldown uses seven days. Stored phases are cleared after seven days;
  anonymous aggregate facts are deleted after 30 days by `python -m app.retention`.
  Sampling and drops must be considered when interpreting trace lists.

## Migration and operations

Apply migration 006 before startup and reapply `deploy/runtime-grants.sql`. Runtime
requires SELECT/INSERT on `operational_executions`; schema owner handles retention.
Migration 006 also records actual input/output token counts in `spend_ledger` for new
settlements, without inventing usage for old rows. Observation rows deliberately have
no conversation foreign key and survive visitor-requested conversation deletion.

Keep `OPS_READ_TOKEN` unset and `OTEL_SDK_DISABLED=true` for ordinary free development.
To test first-party measurements, set a disposable token, full `OPS_API_COMMIT` and
`OPS_TRACE_SAMPLE_RATIO=1` in an isolated fixture process. To enable export, additionally
set `OTEL_SDK_DISABLED=false` and a private origin such as
`OTEL_PRIVATE_ENDPOINT=http://collector:4318`. This is configuration, not permission
to deploy a collector or send data to an external vendor.

Run `uv run pytest -q tests/test_private_observability.py` for auth/schema, stream cleanup,
bounded buffering, safe logging and an actual loopback OTLP protobuf receiver. The
integration suite verifies real PostgreSQL persistence, deletion independence, trace
retention window and the status endpoint. No paid model call is required.

Release gates remain effective private routing, actual exporter/collector connectivity,
Grafana/Prometheus access policy, container scan findings, measured VPS capacity,
backups, retention scheduling and paired authenticated-browser review.

Backoffice runtime names are `OPERATIONS_API_ORIGIN` (private API origin) and
`OPERATIONS_READ_TOKEN` (same value as API `OPS_READ_TOKEN`). These are server-only.
Omit `OPERATIONS_SOURCE_MODE` in production. The deployed API source revision goes
in `OPS_API_COMMIT`; it is not a secret. No registry credentials are supplied here.
