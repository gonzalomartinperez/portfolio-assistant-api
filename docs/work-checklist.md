# Three-deliverable acceptance checklist

Single priority/status checkpoint for the consolidated mandate. Preserve existing
work, six-layer boundaries and v1 consumers. Use checked PRs into **develop only**;
no main promotion, paid calls, artifact publication or production execution is
authorized. Critical security issues interrupt the sequence below.

Current audited implementation: `15b6943` (PR #34), 196 tests passed on
2026-10-04. Earlier tables retain dated increment evidence. The detailed open
findings, owners and closure criteria are maintained once in
[live-evaluation readiness](live-evaluation-readiness.md): A1 harness isolation;
A2 live quality; A3 frontend adoption; A4 promotion controls; A5 dependency
activation; A6 corpus retention; A7 public projection; A8 operations. A9 closes
documentation drift only. None of these pending runtime/external gates is complete
merely because its handoff is documented.

| Priority / deliverable | Acceptance criterion | Status and evidence |
| --- | --- | --- |
| 1 Conversations | Direct public evidence, bounded bilingual context, safe topic changes and role-fit retrieval | Implemented history/evidence separation and answer-first provider contract in #19; source 5742961 fixes named-example topic changes, reference refinements and target-role parsing. Actual fixture comparisons in the evaluation guide; live reasoning/tone unverified. |
| 1 Compatibility | Published HTTP/SSE, sessions/history, true provider streaming, cancellation and interruption | v1 artifacts unchanged. Frontend a9a85bb consumes snapshot 6b1e65f; current handoff pins compatible 5742961. `/embed` primary, `/` demo, same-origin API. Committed embed protocol reviewed; browser verification remains the frontend owner’s gate. |
| 2 Security and reliability | Ownership, isolation, Origin/CSRF, atomic budgets, limits, recovery and safe ingestion | Existing suite covers these controls; #22 added serialized provider-input budget guard. Current increment tests assistant-only Origin with host-scoped Secure cookie and rejected parent-origin mutations. |
| 3 Backend quality | Architecture, Google-adapted Python conventions, typing, real databases, migrations, retrieval, image/proxy smoke | Prior latest CI passed 85 tests (67 offline + 18 integration), image and proxy checks. Current local source 5742961 passes 97 tests, lint, typing, contract drift and skill validation; current-head Actions remains the merge gate. |
| 4 Skills | Small canonical catalog, portable discovery, meaningful validation | Complete: five canonical `.claude/skills` with relative Codex links, validator and 12 tests. Codex discovery and Claude discovery/expansion tested; natural-language model selection remains unverified. See agent-skills.md. |
| 5 CI | Pinned actions, parallel checks, minimal permissions, required aggregate, failure artifacts | Implemented; Dependabot #17/#18 merged. Actual final prior run 36332774736 passed (static 22s, integration/container 92s, gate 2s). PR #23 current-head Actions passed. New dependency-policy work requires its own checked PR. |
| 6 Deployment handoff | API image/runtime/migrations for Coolify managed by vps-ops | Application contract complete; current update supersedes direct portfolio access with same-origin `/embed` target. Production publication, Coolify and VPS tests remain unauthorized/unverified. Frozen shared templates are transfer references only. |
| Final | Reviewed increment, current-head CI, committed contracts and exact results | Backend increment integrated by PR #23 at 4186664 after current-head CI. Dependency automation is a separate CI increment; GitHub is authoritative for merge status. No main or production action. |

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
retrieve/answer flow remains intentional; no paid evaluation or deployment authorized.

## Remaining external gates and deferred work

- **Blocked on authorization:** live-model usefulness, role-fit reasoning, bilingual
  personality and adversarial evaluation; fixture excerpts cannot prove these.
- **Pending coordination:** paired `/embed` browser evidence and frontend deployment-document
  reconciliation with its newly committed embed protocol. Continue independent API checks; never consume mutable sibling files.
- **Deferred:** real portfolio integration and cross-tab conversation transfer.
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
See [scope, tests and activation handoff](dependency-updates.md). This is part of
repository quality; it adds no deployment controller or main promotion authority.

## Question coverage increment

100 intent families / 1000 question variations (500 per locale hint), plus the
existing 40 adversarial prompts. Canonical source and deterministic compiler prevent
copy drift; family-level splits protect holdout isolation. Fixture execution and
current-head CI are the verification gates. Live answer quality remains unverified;
question count is coverage, not additional approved biographical facts.
