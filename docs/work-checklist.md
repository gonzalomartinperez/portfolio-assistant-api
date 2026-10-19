# Three-deliverable acceptance checklist

Current checkpoint: 2026-10-19. This replaces the earlier October status table;
historical counts and decisions remain in their dated verification reports and Git
history. Keep source acceptance separate from production acceptance. Each invocation
needs its own authority for main promotion, publication, external exports or paid
calls; a merged plan grants none of those permissions.

| Priority / deliverable | Implemented and verified | Remaining acceptance |
| --- | --- | --- |
| 1 Conversations and compatibility | Native portfolio HTTP/SSE contract, optional bounded visitor context, ownership/CSRF, history/cancellation, bilingual voice and source mapping. Product events and current-rating summaries are private, validated and default-off. | The portfolio owner controls activation. Broader model factuality and physical-device acceptance remain separate from fixture and bounded live evidence. |
| 1 Security and reliability | Explicit provider origin, verified TLS, no redirects or inherited proxy/CA environment, zero generation retries, constructor ownership and independent resource cleanup. Pure policy and architectural negative tests remain mandatory. | Native TLS negotiation and future VPS load are not certified by synthetic transport tests. API and Neo4j security acceptance remain blocked. |
| 2 Repository quality and skills | Five canonical skills with relative Codex discovery links, maintained structural/scenario checks, strict inner-layer mypy, capability adapter packages and pinned parallel CI. Standard MIT software licensing retains separate content rights. | Model-based skill selection and untested client versions are not certified. Existing checks and review requirements remain authoritative. |
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

## Current source increments

- **Completed:** PR113–117, final source promotion/synchronization, root-content
  RAG readiness and pinned/cached CI. Main f9c0f0a and develop 6ad190b share the same
  tree; both post-merge six-job runs passed 819 offline and 47 real-service tests.
  [Final local artifact evidence](verification/final-artifact-closeout-2026-10-18.md)
  records the corrected payload, 183-package inventory/184-component SBOM,
  preserved archive-harness failures and the API/Neo4j production security holds.
  No new paid campaign, publication or deployment was authorized.

- **Completed:** PR91/92 calendar analytics, real native-ingest/readback evidence and
  tooling cleanup fixes. [Calendar verification](https://github.com/gonzalomartinperez/portfolio-backoffice/blob/14c9e11ca42e2b47d26dc5ef55c9f0eef33512a5/docs/verification/calendar-integration-2026-10-18.json)
  is a safe aggregate receipt; it contains no credentials or conversation data.
- **Completed:** PR93 canonical capability adapters and explicit bootstrap defaults;
  source8722bbefe31a227e7b9987cc1e20b13431f1d8e9 passed671offline and37real-service
  tests in [CI39091167785](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/39091167785).
  [Dated architecture evidence](verification/common-layout-results-2026-10-18.md)
  records SQL checksum/CLI/negative-boundary tests and independent review.
- **Completed:** PR94 application-only Docker layout and retired production
  controller;676offline and37real-service tests passed in CI39091552603.
  Develop mergecf3b68be8ddd45460d8156ac73d6eaf175e04d99; see
  [the path/ownership handoff](docker-layout-handoff.md).
- **Completed:** PR95 paired six-job CI profile, exact-source identity,
  fail-closed aggregate and read-back protection bridge on develop/main.
  CI39092548386passed every job at9a7b97c before normal merge
  923f5d32215203d6a09efd2ef1dec8e49225d4e5. Post-merge runs remain separately
  attributed. Post-develop39093024368 correctly failed closed on a fresh PostgreSQL
  initialization race. PR99 adds final-postmaster readiness and a delayed-initdb
  regression; CI39093823788 passed696offline and38real-service tests before
  normal mergea5707b24bf1853e44b9888794bcfb7575e462cea. No image archive or publication
  was introduced.
- **Completed:** manually reviewed Dependabot96/97/98 cohort, normal PR100 merge
  633b7ecbe8141ddf505deba42c21e418c460f5c2 after all six jobs passed
  CI39094247058. The rebased duplicate97 workflow blob exactly matched develop and
  was closed without suppressing alerts. [Review scope](verification/dependency-cohort-2026-10-18.md)
  records the meaningful runtime changes and original failed fixture run.
- **Completed:** final audit fixes isolate chunk identities across embedding profiles
  (6c26f3915a45762c8de1755fbbd840f8ef217a87) and durably retain private evaluation
  progress (aa9bbeae3bb5e2e156917f9b07b1150a2f800718). Each has observed RED/GREEN
  regressions and independent source review. CI39094723647 passed all six jobs:
  723offline and40real-service tests, including both provider-switch directions.
  The new encoder transport remained synthetic; no new model calls.
- **Completed:** root project1.0 metadata, automatic skill policy negatives and
  actual client-discovery evidence are included in the verified sourcef6990fc.
  Wire schema versions remain independent; no final tag or production readiness is
  inferred from a package version. Main/final promotion remains coordinated.

## Production blockers and owner handoffs

- **Blocked:** [Neo4j vendor acceptance](verification/neo4j-vendor-refresh-2026-10-17.md).
  The rejected candidate does not replace the retained digest. A normal API/PG
  image scan does not assess the full Neo4j Java inventory. Do not suppress the
  critical/fixable-high findings or patch vendor jars.
- **Migration constraint:** a rollback reader must retain every applied migration through009 and
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
