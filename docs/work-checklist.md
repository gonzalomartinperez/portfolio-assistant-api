# Three-deliverable acceptance checklist

Single priority/status checkpoint for the consolidated mandate. Preserve existing
work, six-layer boundaries and v1 consumers. Use checked PRs into **develop only**;
no main promotion, artifact publication or production execution is authorized.
Critical security issues interrupt the sequence below. Paid calls require explicit
scope/budget; the dated experiment below does not authorize ongoing usage.

Current integrated checkpoint: `a3f9b7ce9fbc9646cec4d6dc17f3ed0d4f371ec1`
(manually reviewed Dependabot PR #31), including database-image PR #41 at
`6cc116609acec823314e94b88fe15137ddd96786`. Both passed actual current-head
Quality runs before merging. Runtime security PR #40 is preserved in this history.
Current contract: `61da393520014ed2c8b1f8a0635b3b4e615f9e53` (PR #36).
Latest [runtime security evidence](verification/runtime-security-2026-10-10.md) and
[database evidence](verification/database-images-2026-10-10.md) supersede earlier
container observations. [CI evidence](ci.md#executed-overnight-verification) identifies
the actual runs; [vps-ops request](vps-ops-request.md) is the committed handoff prompt.
[2026-10-10 evidence and blockers](verification/runtime-2026-10-10.md) records
237 real-service tests, image/proxy checks, source revisions and the bounded
real-provider experiment. The older [readiness audit](live-evaluation-readiness.md)
retains its dated closure criteria; neither document grants additional authority.

| Priority / deliverable | Acceptance criterion | Current status and evidence |
| --- | --- | --- |
| 1 Conversations | Grounded bilingual answers, correct citations and topic changes | Observed citation mapping and Spanish topic-switch defects fixed in PR #39, with pure, streaming, HTTP/history and fixture continuity regressions. Three real-provider turns revalidated final citations/history and the observed Spanish topic switch; broader claim-support quality remains pending. |
| 1 Compatibility | Stable HTTP/SSE, optional visitor context, sessions/history/cancellation | Context validated and mapped separately from evidence in PR #36; OpenAPI/examples committed, legacy clients preserved. Native portfolio contract import/browser pairing pending with its owner; rollout remains disabled. |
| 2 Security/reliability | Ownership, CSRF, isolation, budgets, termination and safe ingestion | Existing controls tested; interruption writes now drain before pool shutdown. Both database isolation guards implemented in PR #39. API image removes base pip/ensurepip bundles: 58 unresolved HIGH findings. Patched PostgreSQL: 3 CRITICAL/65 HIGH, none fixable in the scan; Neo4j: 1 CRITICAL/113 HIGH, including vendor Java fixes. Full reports retained, no suppression. Production assessment remains blocked. |
| 3 Backend quality | Strict boundaries/types, real persistence and image/proxy evidence | 291 tests including shutdown-ordering and database-image provenance regressions on Python 3.14.8, Ruff/format, strict mypy, frozen install, contract/Compose/skills checks; final non-root image streaming, SIGTERM and proxy/disconnect checks pass. PR #41 current-head CI passed; 25 real-service tests also confirmed in downloaded CI diagnostics. |
| 4 Skills | Focused canonical catalog and portable discovery | Five canonical skills with relative Codex links, validator/scenarios; previously exercised client discovery. Updated release skill reflects application/database scope. Model-based natural-language selection remains unverified. |
| 5 CI/dependencies | Pinned parallel checks, minimal permissions, protected merges | PR #41 actual static 36 s, integration 219 s, gate 3 s; PR #31 actual 30/148/3 s. Strict develop freshness and required checks verified. Actions major PR #31 manually reviewed and merged; unattended dependency automation remains inactive. |
| 6 Deployment handoff | Image/runtime/databases for vps-ops-managed Coolify | Contract and committed vps-ops master request updated with local database ceilings, the tested non-root PostgreSQL image, runtime-only configuration, native CORS and backoffice ownership. VPS allocation, image publication, production execution and recovery validation remain unverified/unauthorized. |
| Final | Integrated increments with precise release recommendation | PRs #36–#41 and manually reviewed dependency PR #31 merged into develop; main untouched. This is a verified application increment, not production release approval. |

The public-knowledge/coverage sections below retain earlier implementation history;
the current table and dated verification define remaining acceptance gates.

## Current public-knowledge increment · 2026-10-03

| Priority | Acceptance | Status |
| --- | --- | --- |
| 1 Current knowledge | Poll approved published main; coalesce revisions; atomic activation; stale knowledge fails closed | Implemented; deterministic worker and real database activation/cache tests. Local worker fetched and indexed main 2f4fb400184b34593fd71f4d5fbf29738496a5a0. No production worker configured. |
| 1 Model and language | OpenAI only, GPT-6 Luna, medium, ES/EN, bounded context, source-supported citations | Implemented adapters/configuration and offline tests. Real paid answer quality remains unverified. |
| 2 Retrieval and budget | Semantic, lexical and graph retrieval; shared USD 10 admission ledger; public embedding cache | Implemented migrations 004/005 and adapters, tested with synthetic provider and real stores. Real embedding precision and paid accounting still require authorized evaluation. |
| 2 Security | No tracing, no provider fallback, safe errors, private cache exclusions, request deadline | Implemented and tested. Local logs remain for operations; no external telemetry enabled. |
| 3 Skills and CI | Update existing focused workflows, retain boundaries and secure runner compatibility | Structural/behavioral regression tests pass; current-head Actions remains the merge gate. |
| 3 Handoffs | Public projection schema, source-backed starter endpoint, Coolify worker/runtime contract | Committed artifacts prepared; portfolio projection publication, frontend import and vps-ops execution remain external gates. |

Pending live evaluation is not a claimed capability. Extra LLM planning/reranking,
budget warning notifications and corpus pruning remain deferred until their need,
cost and operational policy are reviewed. The existing deterministic LangGraph
retrieve/answer flow remains intentional. A bounded paid evaluation was authorized
and executed on 2026-10-10; production and further paid scope are separate decisions.

## Remaining external gates and deferred work

- **Implemented:** citation/context regressions and both harness isolation guards.
  **Verified:** bounded three-turn real-provider revalidation. Broader claim-support
  review remains pending. Thirteen single-turn terminals do
  not establish broad answer quality.
- **Pending coordination:** native portfolio context import/browser evidence and
  the missing private operations contract for real backoffice metrics. Consume
  only committed snapshots; fixture dashboards are not integration proof.
- **Deferred:** enabling the real portfolio assistant; cross-tab transfer is not
  a release requirement.
- **Outside application ownership:** Coolify/Traefik, DNS/TLS, resource allocation,
  encrypted off-server restoration and deployment belong to private vps-ops.
  Runtime contract is ready for its review; no registry digest exists until an
  explicitly authorized publication. Default planned package visibility is private.
- **Owner decision:** source license remains unspecified. No new infrastructure,
  framework or optional action protocol is needed to finish this increment.

Backend UX, repository skills and runtime handoff are the three deliverables.
Security, architecture, testing, coding style and CI are acceptance criteria across
them, not additional projects. Historical main promotion does not authorize another.


## Requested CI maintenance increment

Conservative Dependabot policy is implemented and locally tested (52 policy cases).
Repository native auto-merge capability is enabled; unattended automation remains
**inactive** until separately authorized required-check/variable activation and
privileged-token verification. Policy files are already on the default branch;
their presence alone does not enable merging. Existing strict protections/reviews
are preserved. Read-only CI token protection-query access is blocked; the
privileged controller must establish access before activation.
Dependabot PR #31 was instead manually reviewed: authenticated bot/source/base,
one bot commit, four pinned action-only changes, signed upstream release and
current-head Quality. No automatic merge eligibility was granted to this major
update. API and backoffice open-PR inventories were empty at the 2026-10-10
05:15 UTC checkpoint; this does not assert that security alerts are empty.
See [scope, tests and activation handoff](dependency-updates.md). This is part of
repository quality; it adds no deployment controller or main promotion authority.

## Question coverage increment

100 intent families / 1000 question variations (500 per locale hint), plus the
existing 40 adversarial prompts. Canonical source and deterministic compiler prevent
copy drift; family-level splits protect holdout isolation. Fixture execution and
current-head CI are the verification gates. Live answer quality remains unverified;
question count is coverage, not additional approved biographical facts.
