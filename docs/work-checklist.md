# Three-deliverable acceptance checklist

This is the single priority/status checkpoint. Preserve the working six-layer
architecture and v1 consumers; integrate task PRs into develop, then promote through a checked PR to main only
after all three deliverables are complete (latest explicit owner authorization). Critical
security findings interrupt the order below. No paid model calls or production
execution are authorized.

| Priority | Acceptance criterion | Status / evidence |
| --- | --- | --- |
| 1 Experience | Audit representative English/Spanish conversations; answer-first evidence, contribution detail, role-fit distinctions, bounded follow-ups and unknowns | In progress: current fixture exposes raw source excerpts; workflow has no prior-turn input. Actual baseline/after run records pending. |
| 1 Compatibility | Preserve HTTP/SSE, real incremental provider cancellation, committed contract and frontend handoff; optional actions only if useful and safe | Existing v1 contract tested; conversational changes pending. No frontend edits. |
| 2 Security | Ownership, CSRF, isolation, budgets, limits, untrusted job descriptions and retrieved text; safe errors and cleanup | Existing controls tested in earlier CI; rerun and add context-specific regressions with functional changes. |
| 3 Verification | Behavior tests, real PostgreSQL/Neo4j, migrations/recovery, retrieval comparisons, image and proxy smoke; before/after evidence | Last completed baseline: 63 tests in CI. Current offline run: 58 passed, 17 integration deselected (includes 12 new skill-validator tests). |
| 4 Presentation | Natural bilingual answers, useful grounded next steps, no unsupported biography or hiring commitments | In progress; fixture improvements will remain explicitly simulated. |
| 5 CI | Secure pinned parallel jobs, deterministic artifacts, required gate, review dependency updates | Existing pipeline implemented and previously verified; current changes need actual PR runs. Dependabot #17/#18 await focused review. |
| 6 Deployment contract | API image/runtime/migration handoff to vps-ops; Coolify selected; no application deployment controller | In progress documentation only; existing shared templates retained for transfer. No Coolify/VPS execution. |
| 7 Skills/docs | Small canonical task catalog, Codex/Claude discovery, structural/behavioral evidence and accurate instructions | Five skills drafted; validator and 12 tests pass. Codex discovery verified; Claude bare probe did not discover skills and needs correction. Not yet integrated. |
| Final | All applicable checks pass on current PR heads; merge develop; exact commits, handoff and limitations reported | Pending. Main promotion waits for all three deliverables and its own required checks. |

## Deliverable mapping

1. **Master UX upgrade (backend):** priorities 1–4 above. Complete grounded, helpful
   bilingual conversations and bounded continuity; preserve HTTP/SSE and publish
   committed frontend contracts. UI, accessibility, avatars and animation are the
   frontend owner's work, not changes in this repository.
2. **Repository skills:** priority 7. One canonical catalog, actual client evidence,
   structural validation and honest behavioral limitations.
3. **Deployment handoff:** priority 6. API artifacts and Coolify runtime requirements
   only; vps-ops owns shared infrastructure and execution.

Architecture, Google-adapted typed Python style, security, CI and verification are
acceptance criteria across all three deliverables, not additional projects. Finish
working increments in this order; do not repeat planning or expand scope.

## Deferred or externally blocked

- Live-model intelligence, tone and injection evaluation: requires explicit paid-use
  authorization and a bounded evaluation budget; fixtures cannot establish these.
- Production image publication: requires authorization and package visibility
  decision. Coolify workflow, DNS/TLS, shared resource allocation, encrypted
  off-server restore and production rollout belong to vps-ops and remain unverified.
- Frontend import of committed API artifacts and any UI changes belong to its owner.
- License selection remains an owner decision. No infrastructure or optional
  framework expansion is part of this phase.
