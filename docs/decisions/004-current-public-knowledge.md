# ADR 004: current public knowledge and one OpenAI generation model

Status: accepted implementation direction; paid evaluation and production pending.

Use the public portfolio main branch as the published knowledge authority. A
separate worker polls approved Git objects, validates staged projections and
atomically activates only the latest observed revision. Currentness is bounded by
poll/index/network latency; stale or known-pending revisions cannot claim freshness.
No runtime dependency on private career-ops or a sibling working tree is allowed.

Keep PostgreSQL 17/pgvector as the authoritative version/vector store and Neo4j
5.26 LTS as a reconstructible relationship projection. Preserve exact vector search
for the small corpus; add ANN only after measured need. Semantic embeddings use
OpenAI text-embedding-3-small with 1536 dimensions. The optional public projection
replaces regex graph extraction after portfolio-owner adoption. No Redis is needed.

Generate only with GPT-6 Luna, explicit medium reasoning, store=False and an initial
8192-token output/reasoning ceiling. No provider/model fallback or automatic billed
retry. The approved application budget is at most USD 10/month, shared by query,
indexing and generation. No externally exported telemetry or tracing is permitted.
Python 3.14 is checked against locked dependencies and the pinned amd64 image.

Coolify runtime variables are sufficient for this initial single-owner deployment.
vps-ops owns secret delivery, off-server encrypted backups and the separate Coolify
APP_KEY recovery material. No Infisical service, app secret SDK or parallel controller
is introduced. CI/image publication cannot authorize production execution.

Tradeoffs: Lingua 2.2.0 adds a substantial native model wheel; low-accuracy mode
limits loaded models but first-use latency/memory must be measured. Polling introduces
a freshness window; withheld answers are preferable to claiming stale facts are current.
Monthly reservations are conservative, especially on interruptions. Keeping retired
versions requires a production retention policy. Additive schemas do not guarantee
rollback to an older image because migration readiness is intentionally strict.

References: [OpenAI reasoning](https://developers.openai.com/api/docs/guides/reasoning),
[pgvector](https://github.com/pgvector/pgvector),
[Python lifecycle](https://devguide.python.org/versions/),
[Coolify recovery](https://coolify.io/docs/core/security-model).
