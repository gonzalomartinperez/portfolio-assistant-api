# Documentation map

Documentation is grouped by the [Diataxis](https://diataxis.fr/) quadrants. Paths are stable: reference and decision
paths do not move after this reorganization, and the link check blocks breakage.

## tutorials

Learn by doing: from clone to a first working result.

- [Deterministic local demo](tutorials/local-development.md)

## how-to

Task recipes for a reader who knows the goal.

- [Operations and future VPS deployment](how-to/deploy-with-vps-ops.md)
- [Disposable analytics integration demo](how-to/local-analytics-demo.md)
- [Continuous public knowledge](how-to/maintain-knowledge.md)
- [Release acceptance entry point](how-to/release.md)
- [Roll back a change on develop](how-to/roll-back-a-change.md)

## reference

Facts to look up: contracts, configuration, policies.

- [Repository agent skills](reference/agent-skills.md)
- [Public API and SSE v1](reference/api-contract.md)
- [CI and release preparation](reference/ci.md)
- [Dependency updates: one weekly PR, merged manually](reference/dependency-updates.md)
- [API runtime handoff to vps-ops](reference/deployment-contract.md)
- [Configuration reference](reference/environment.md)
- [Assistant quality evaluation](reference/evals.md)
- [Frontend integration handoff](reference/frontend-handoff.md)
- [Product analytics v1 — local, disabled by default](reference/product-analytics.md)
- [Repository settings (live record)](reference/repo-settings.md)
- [Runtime baseline acceptance — 2026-10-17](reference/runtime-baseline.md)
- [Scorecard tooling](reference/scorecard.md)
- [Site experience interoperability · v1](reference/site-experience-contract.md)
- [Supported versions and upgrade policy](reference/support-policy.md)
- [Manual synthetic evaluation export](reference/synthetic-evaluation-export.md)
- [Analytics direct-edge contract · v1](reference/contracts/analytics-direct-edge-v1.md) (cross-repo contract)
- [Public assistant-knowledge handoff](reference/contracts/portfolio-assistant-knowledge.md) (cross-repo contract)
- [Public content layout compatibility](reference/contracts/portfolio-content-layout.md) (cross-repo contract)

## explanation

Background and reasoning behind the design.

- [Architecture and responsibilities](explanation/architecture.md)
- [Assistant voice](explanation/assistant-voice.md)
- [Assistant gallery, light and dark](explanation/gallery.md)
- [Portfolio-first tools and optional web context](explanation/bounded-web-context.md)
- [Engineering coordination · 2026-10-17](explanation/engineering-coordination.md)
- [Voluntary context and evidence-based improvement](explanation/feedback-and-improvement.md)
- [Retrieval pipeline and rule ablation](explanation/retrieval.md)
- [Public knowledge and GraphRAG](explanation/graph-retrieval.md)
- [Private observability and backoffice contract](explanation/private-observability.md)
- [Threat model and privacy](explanation/threat-model.md)

## decisions, evidence and plan

- [Decision records](decisions/README.md): ADR index.
- [Evidence](evidence/README.md): dated records and the 2026-10 archive.
- [Master plan](master-plan/README.md): the refactor plan and progress log.
