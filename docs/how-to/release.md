# Release acceptance entry point

Status and priorities live in the [roadmap progress log](../master-plan/progress.md)
and in GitHub issues, not in prose checklists. Architecture, security, coding,
migrations, contracts and CI remain cross-cutting gates, with evidence linked from the
pull request and the [evidence index](../evidence/README.md).

Before a first real-provider test or release claim, review the
[2026-10-04 audit and closure criteria](../evidence/archive/2026-10/live-evaluation-readiness.md). It separates
implemented fixture evidence from runtime fixes, authorized evaluation and external
owner gates. The historical records below do not replace this current checkpoint.

The earlier fixture release evidence remains in
[backend-rc.json](../evidence/archive/2026-10/backend-rc.json); current conversational/client/image
verification is in [ux-release.json](../evidence/archive/2026-10/ux-release.json). Historical runs
are not a substitute for required checks on the current PR head.

Main promotion requires current explicit authorization and its own PR gate.
Production deployment and image publication require separate authorization; Coolify
execution belongs to private vps-ops. Live-model quality, model-driven skill routing,
VPS capacity and encrypted off-server recovery remain unverified. Application
software uses MIT with separate identity/content and third-party notices. Never infer production readiness from fixture test success.
