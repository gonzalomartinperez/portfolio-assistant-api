# Three-deliverable acceptance checklist

Single priority/status checkpoint for the consolidated mandate. Preserve existing
work, six-layer boundaries and v1 consumers. Use checked PRs into **develop only**;
no main promotion, paid calls, artifact publication or production execution is
authorized. Critical security issues interrupt the sequence below.

| Priority / deliverable | Acceptance criterion | Status and evidence |
| --- | --- | --- |
| 1 Conversations | Direct public evidence, bounded bilingual context, safe topic changes and role-fit retrieval | Implemented history/evidence separation and answer-first provider contract in #19; source 5742961 fixes named-example topic changes, reference refinements and target-role parsing. Actual fixture comparisons in the evaluation guide; live reasoning/tone unverified. |
| 1 Compatibility | Published HTTP/SSE, sessions/history, true provider streaming, cancellation and interruption | v1 artifacts unchanged. Frontend a9a85bb consumes snapshot 6b1e65f; current handoff pins compatible 5742961. `/embed` primary, `/` demo, same-origin API. Committed embed protocol reviewed; browser verification remains the frontend owner’s gate. |
| 2 Security and reliability | Ownership, isolation, Origin/CSRF, atomic budgets, limits, recovery and safe ingestion | Existing suite covers these controls; #22 added serialized provider-input budget guard. Current increment tests assistant-only Origin with host-scoped Secure cookie and rejected parent-origin mutations. |
| 3 Backend quality | Architecture, Google-adapted Python conventions, typing, real databases, migrations, retrieval, image/proxy smoke | Prior latest CI passed 85 tests (67 offline + 18 integration), image and proxy checks. Current local source 5742961 passes 97 tests, lint, typing, contract drift and skill validation; current-head Actions remains the merge gate. |
| 4 Skills | Small canonical catalog, portable discovery, meaningful validation | Complete: five canonical `.claude/skills` with relative Codex links, validator and 12 tests. Codex discovery and Claude discovery/expansion tested; natural-language model selection remains unverified. See agent-skills.md. |
| 5 CI | Pinned actions, parallel checks, minimal permissions, required aggregate, failure artifacts | Implemented; Dependabot #17/#18 merged. Actual final prior run 36332774736 passed (static 22s, integration/container 92s, gate 2s). Current head must pass independently. |
| 6 Deployment handoff | API image/runtime/migrations for Coolify managed by vps-ops | Application contract complete; current update supersedes direct portfolio access with same-origin `/embed` target. Production publication, Coolify and VPS tests remain unauthorized/unverified. Frozen shared templates are transfer references only. |
| Final | Reviewed increment, current-head CI, committed contracts and exact results | Local implementation/verification complete; integrate through the current-head checked PR into develop. GitHub is authoritative for merge status. No main or production action. |

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
