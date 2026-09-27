# Release acceptance entry point

The single prioritized, three-deliverable checklist is
[Active delivery acceptance](work-checklist.md). Keep status and priorities there.
Architecture, security, coding, migrations, contracts and CI remain cross-cutting
gates, with evidence linked from that checklist and IMPLEMENTATION_STATUS.md.

The earlier fixture release evidence remains in
[backend-rc.json](verification/backend-rc.json); current conversational/client/image
verification is in [ux-release.json](verification/ux-release.json). Historical runs
are not a substitute for required checks on the current PR head.

Main promotion requires current explicit authorization and its own PR gate.
Production deployment and image publication require separate authorization; Coolify
execution belongs to private vps-ops. Live-model quality, model-driven skill routing,
VPS capacity and encrypted off-server recovery remain unverified. No source license
has been selected. Never infer production readiness from fixture test success.
