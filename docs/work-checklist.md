# Three-deliverable acceptance checklist

Current checkpoint: 2026-10-17. This replaces the earlier October status table;
historical counts and decisions remain in their dated verification reports and Git
history. Keep source acceptance separate from production acceptance. Each invocation
needs its own authority for main promotion, publication, external exports or paid
calls; a merged plan grants none of those permissions.

| Priority / deliverable | Implemented and verified | Remaining acceptance |
| --- | --- | --- |
| 1 Conversations and compatibility | Native portfolio HTTP/SSE contract, optional bounded visitor context, ownership/CSRF, history/cancellation, bilingual voice and source mapping. Product events and current-rating summaries are private, validated and default-off. | The portfolio owner controls activation. Broader model factuality and physical-device acceptance remain separate from fixture and bounded live evidence. |
| 1 Security and reliability | Explicit provider origin, verified TLS, no redirects or inherited proxy/CA environment, zero generation retries, constructor ownership and independent resource cleanup. Pure policy and architectural negative tests remain mandatory. | Native TLS negotiation and future VPS load are not certified by synthetic transport tests. Neo4j security acceptance is blocked. |
| 2 Repository quality and skills | Five canonical skills with relative Codex discovery links, maintained structural/scenario checks, strict mypy, pinned parallel CI and standard MIT software licensing with separate content rights. | Model-based skill selection and untested client versions are not certified. Existing checks and review requirements remain authoritative. |
| 3 Runtime and integration handoff | Application images, private OPS/product/feedback contracts, PostgreSQL artifact, measured database access paths and Coolify runtime/migration contract. | Immutable image publication, registry visibility, real OAuth, shared monitoring, VPS resources, effective routing/headers and recovery belong to separately authorized verification. |

## Evidence and revisions

- [Bounded live smoke](verification/bounded-live-smoke-2026-10-17.md): exact API
  `02b6f2784564669597fe8a4c2adf53bf807737a6`, portfolio corpus
  `776ee8613d3cc78bc3afb5a4609d5edbfd16ada3`. Six completed cases, five actual model
  generations and one local policy response; 100 real embeddings. This is not a
  new 200-question campaign or proof of every supported claim. No ongoing paid
  allowance follows from that experiment.
- [Provider transport and cleanup](verification/provider-transport-2026-10-17.md):
  runtime commit `9ad866c2bf92a857df12bdf58d04fbf70c6ca520`, 537 offline tests;
  service/container CI is the independent merge gate in PR84.
- [Database access paths](verification/database-queries-2026-10-17.md): PR81,
  migration008, 507 offline / 33 real-service tests at that increment. Synthetic
  plan/latency results are not production capacity or semantic-retrieval recall.
- [Manual LangSmith aggregate export](synthetic-evaluation-export.md): PR80,
  offline by default, explicit authorization needed for any external export.
  No automatic tracing or real LangSmith account was activated.
- Software licensing: PR82, 518 offline / 33 real-service tests at that increment.
  [MIT](../LICENSE) applies to application software; personal/reference content,
  marks and dependencies retain [their separate rights](../THIRD_PARTY_NOTICES.md).
- [Runtime compatibility](verification/runtime-compatibility-2026-10-17.md),
  [runtime baseline](runtime-baseline.md), [CI job purposes](ci.md) and
  [actual gallery capture provenance](verification/readme-gallery.md) retain their
  own evidence and limitations. Counts above identify increments, not a combined
  test total. Later required CI runs supersede earlier source checkpoints.

## Production blockers and owner handoffs

- **Blocked:** [Neo4j vendor acceptance](verification/neo4j-vendor-refresh-2026-10-17.md).
  The rejected candidate does not replace the retained digest. A normal API/PG
  image scan does not assess the full Neo4j Java inventory. Do not suppress the
  critical/fixable-high findings or patch vendor jars.
- **Migration constraint:** a rollback reader must retain applied migration008 and
  its checksum. Reverting an application image does not undo schema changes;
  pre008 images fail strict readiness. See [deployment contract](deployment-contract.md).
- **Owner decisions:** dependency maintenance is manual; native auto-merge is off.
  Keep default-branch security updates visible and require reviewed current-head
  CI. See [maintenance policy](dependency-updates.md).
- **Deferred:** public assistant and product collection activation, production
  deployment and external telemetry/export. The portfolio owner owns the native
  launcher/chat; the separate web repository is the authenticated backoffice.
- **Outside this repository:** vps-ops owns Coolify, the single reverse proxy,
  production networks, DNS/TLS, shared resources, encrypted off-server backups,
  restart/reboot acceptance and rollback orchestration. Application source merging
  does not authorize those actions or establish VPS readiness.

## Knowledge and evaluation scope

The maintained bank contains 100 intent families / 1,000 question variations,
500 per locale hint, plus 40 adversarial prompts. It is a coverage asset, not
1,000 biographical facts or 1,000 live evaluations. Only approved public portfolio
content enters the runtime corpus. Polling coalesces committed published revisions
and activates a validated corpus atomically; no private career-ops content is used.

Exact vector search remains intentional at the measured corpus size. Additional
planning/reranking, ANN, extra services, budget notifications and retired-corpus
pruning require demonstrated need and reviewed operational policy. Preserve the
finite acceptance criteria rather than adding unrelated infrastructure.
