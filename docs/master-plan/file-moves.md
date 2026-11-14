# File moves, renames, splits and deletions

Source of truth: [file-index.csv](file-index.csv) (every tracked file at `origin/develop` `e749ca7`, 394 files). This page lists every non-`keep` action with its motive, grouped so a reviewer can approve a move family at once. Execution order and acceptance are in [roadmap.md](roadmap.md); a move PR is mechanical, one family per PR, and must keep `ci-gate` green.

There are no `.js`, `.mjs` or `.cjs` files in this repository (Python plus two shell scripts), so the TypeScript destination rule of ecosystem 10.1 has nothing to migrate. Shell scripts: `scripts/fixture-env.sh` stays (sourced by humans, 10 lines, no Python equivalent worth the churn); `scripts/check_workflows.sh` is deleted in favour of the shared actionlint and zizmor job.

## Summary by action

| Action | Files |
|---|---|
| move | 175 |
| keep | 81 |
| archive | 65 |
| rewrite | 40 |
| delete | 22 |
| replace | 7 |
| split | 2 |
| merge | 2 |

## Package move `app/` to `src/portfolio_assistant/` (PAA-D10)

One mechanical PR in M4: `git mv`, codemod of imports (`app.` to `portfolio_assistant.`) in code, tests, scripts, Dockerfile and docs, then the guard and contracts regenerate. Motive: ecosystem 10.2 requires `src/`; avoids importing from the repo root by accident; the generic package name `app` collides in tooling. Zero wire-contract change.

77 files; the rule is `app/<rel>` to `src/portfolio_assistant/<rel>`; the complete list is in file-index.csv (action `move`, reason starting "src layout and package rename"). Files with typing or coverage debt carry it in their reason column, which becomes the work queue for M3 and M4.

## Package move with additional work (entry points, refactors)

Each file is listed with its extra motive in the table below (complexity, coverage, typing, prompt extraction, layout neutrality).

| From | To | Action | Motive |
|---|---|---|---|
| `app/adapters/portfolio/indexing.py` | `src/portfolio_assistant/adapters/portfolio/indexing.py` | move | src layout; _sync CC 28 split; coverage 71% raised with integration tests; mypy strict 16 errors to fix; CC>10:_sync=28 |
| `app/adapters/providers/answer.py` | `src/portfolio_assistant/adapters/providers/answer.py` | rewrite | Inline unversioned developer prompt (about 4.5 KB f-string) extracted to versioned prompt files; stream() CC 16 reduced; prompt_version recorded (PAA-D7); mypy strict 1 errors to fix; CC>10: stream=16 |
| `app/adapters/providers/voice.py` | `src/portfolio_assistant/adapters/providers/voice.py` | rewrite | Voice instruction text moves to versioned prompt fragment; code keeps selection only |
| `app/adapters/providers/web_search.py` | `src/portfolio_assistant/adapters/providers/web_search.py` | move | src layout; search CC 19 reduced; mypy strict 5 errors to fix; CC>10: search=19 |
| `app/adapters/retrieval.py` | `src/portfolio_assistant/adapters/retrieval.py` | move | src layout; coverage 51% raised; becomes the candidates adapter of the retrieval pipeline; mypy strict 5 errors to fix; coverage 51% |
| `app/ai/retrieval.py` | `src/portfolio_assistant/ai/retrieval/ (pipeline.py, fusion.py, rules.py, rules.toml, candidates.py)` | split | Split search() (CC 48) into a declarative pipeline with standard RRF and per-rule ablatable boosts (PAA-D18, v1 A1); metrics gate: golden 100% and recall ratchet unchanged; CC>10: search=48 |
| `app/application/runs.py` | `src/portfolio_assistant/application/runs.py` | move | src layout; _execute CC 15 reduced; CC>10:_execute=15 |
| `app/bootstrap/config.py` | `src/portfolio_assistant/bootstrap/config.py` | rewrite | Frozen BaseSettings with SecretStr and extra=forbid; safe_configuration CC 26 split into validators; env schema published; mypy strict 2 errors to fix; CC>10: safe_configuration=26 |
| `app/bootstrap/container.py` | `src/portfolio_assistant/bootstrap/container.py` | rewrite | create_app CC 21 and lifespan CC 19 split into builders; composition root stays here; mypy strict 30 errors to fix; CC>10: create_app=21, lifespan=19 |
| `app/domain/evidence.py` | `src/portfolio_assistant/domain/evidence.py` | move | src layout; lexical_score CC 11 reduced to <=10; CC>10: lexical_score=11 |
| `app/domain/fixture.py` | `src/portfolio_assistant/adapters/providers/fixture_answer.py + src/portfolio_assistant/adapters/portfolio/source_format.py` | split | Domain must be portfolio-format free: TS-format knowledge moves to the portfolio source adapter, fixture answer text to the fixture provider (CC 21); CC>10: fixture_message=21 |
| `app/domain/graph.py` | `src/portfolio_assistant/domain/graph.py` | move | src layout; facts() CC 12 reduced; coverage 69% raised; coverage 69%; CC>10: facts=12 |
| `app/domain/portfolio_paths.py` | `src/portfolio_assistant/domain/portfolio_paths.py` | move | Becomes the single layout-neutral canonicalizer (src/content vs content) used by indexing, citations, qrels and golden gold-evidence keys (P0 fix, PAA-D3) |
| `app/knowledge_sync.py` | `src/portfolio_assistant/bootstrap/entrypoints/knowledge_sync.py` | move | Entry point under bootstrap; untyped calls fixed; mypy strict 1 errors to fix |
| `app/knowledge_watch.py` | `src/portfolio_assistant/bootstrap/entrypoints/knowledge_watch.py` | move | Entry point under bootstrap; 0% covered, test added; runs in the worker image target; mypy strict 2 errors to fix; coverage 0% |
| `app/main.py` | `src/portfolio_assistant/bootstrap/entrypoints/api.py` | move | Entry point under bootstrap; image CMD and docs updated; deploy-contract change recorded for vps-ops lock |
| `app/migrate.py` | `src/portfolio_assistant/bootstrap/entrypoints/migrate.py` | move | Entry point under bootstrap; console script assistant-migrate; deploy contract refreshed |
| `app/retention.py` | `src/portfolio_assistant/bootstrap/entrypoints/retention.py` | move | Entry point under bootstrap; 0% covered, test added; coverage 0% |

## Tests regrouped by lane

Motive: 58 flat files make the lane of each test invisible; the lanes (unit, integration, contract, architecture, evals, harness, tooling) map one-to-one to CI profiles and to the testing catalog.

| From | To | Action | Motive |
|---|---|---|---|
| `tests/test_adapter_layout.py` | `tests/architecture/test_adapter_layout.py` | move | architecture/boundary lane next to import-linter contracts |
| `tests/test_analytics_country.py` | `tests/unit/test_analytics_country.py` | move | offline unit lane |
| `tests/test_analytics_demo.py` | `tests/tooling/test_analytics_demo.py` | move | tests of repository tooling scripts |
| `tests/test_analytics_periods.py` | `tests/unit/test_analytics_periods.py` | move | offline unit lane |
| `tests/test_architecture.py` | `tests/architecture/test_architecture.py` | move | architecture/boundary lane next to import-linter contracts |
| `tests/test_assistant_voice.py` | `tests/evals/test_assistant_voice.py` | move | tests of graders, evaluators and eval isolation; assistant-quality lane |
| `tests/test_ci_profile.py` | `tests/harness/test_ci_profile.py` | move | harness checks (CI profile coverage, skills, license, release) |
| `tests/test_citation_mapping.py` | `tests/evals/test_citation_mapping.py` | move | tests of graders, evaluators and eval isolation; assistant-quality lane |
| `tests/test_container_layout.py` | `tests/architecture/test_container_layout.py` | move | architecture/boundary lane next to import-linter contracts |
| `tests/test_content_root_compatibility.py` | `tests/unit/test_content_root_compatibility.py` | move | offline unit lane |
| `tests/test_content_root_integration.py` | `tests/integration/test_content_root_integration.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_contract.py` | `tests/contract/test_contract.py` | move | contract lane (oasdiff, schema examples) |
| `tests/test_conversation_context.py` | `tests/unit/test_conversation_context.py` | move | offline unit lane |
| `tests/test_conversation_evaluator.py` | `tests/evals/test_conversation_evaluator.py` | move | tests of graders, evaluators and eval isolation; assistant-quality lane |
| `tests/test_database_benchmark.py` | `tests/tooling/test_database_benchmark.py` | move | tests of repository tooling scripts |
| `tests/test_database_queries.py` | `tests/integration/test_database_queries.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_database_security_receipt.py` | `tests/tooling/test_database_security_receipt.py` | move | tests of repository tooling scripts |
| `tests/test_evaluation_export.py` | `tests/unit/test_evaluation_export.py` | move | offline unit lane |
| `tests/test_evaluation_isolation.py` | `tests/evals/test_evaluation_isolation.py` | move | tests of graders, evaluators and eval isolation; assistant-quality lane |
| `tests/test_evaluation_progress.py` | `tests/evals/test_evaluation_progress.py` | move | tests of graders, evaluators and eval isolation; assistant-quality lane |
| `tests/test_feedback_overview.py` | `tests/unit/test_feedback_overview.py` | move | offline unit lane |
| `tests/test_graph_readiness.py` | `tests/unit/test_graph_readiness.py` | move | offline unit lane |
| `tests/test_grounded_assistant.py` | `tests/evals/test_grounded_assistant.py` | move | tests of graders, evaluators and eval isolation; assistant-quality lane |
| `tests/test_image_security.py` | `tests/tooling/test_image_security.py` | move | tests of repository tooling scripts |
| `tests/test_index_identity.py` | `tests/unit/test_index_identity.py` | move | offline unit lane |
| `tests/test_index_identity_integration.py` | `tests/integration/test_index_identity_integration.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_integration.py` | `tests/integration/test_integration.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_interaction_integration.py` | `tests/integration/test_interaction_integration.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_interaction_models.py` | `tests/unit/test_interaction_models.py` | move | offline unit lane |
| `tests/test_knowledge.py` | `tests/integration/test_knowledge.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_license.py` | `tests/harness/test_license.py` | move | harness checks (CI profile coverage, skills, license, release) |
| `tests/test_live_depth_regressions.py` | `tests/evals/test_live_depth_regressions.py` | move | tests of graders, evaluators and eval isolation; assistant-quality lane |
| `tests/test_operations.py` | `tests/unit/test_operations.py` | move | offline unit lane |
| `tests/test_presentation_context.py` | `tests/unit/test_presentation_context.py` | move | offline unit lane |
| `tests/test_private_observability.py` | `tests/unit/test_private_observability.py` | move | offline unit lane |
| `tests/test_product_analytics.py` | `tests/unit/test_product_analytics.py` | move | offline unit lane |
| `tests/test_product_analytics_integration.py` | `tests/integration/test_product_analytics_integration.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_project_database.py` | `tests/integration/test_project_database.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_project_fixture_readiness.py` | `tests/tooling/test_project_fixture_readiness.py` | move | tests of repository tooling scripts |
| `tests/test_project_postgres_fixture.py` | `tests/tooling/test_project_postgres_fixture.py` | move | tests of repository tooling scripts |
| `tests/test_project_postgres_platform.py` | `tests/integration/test_project_postgres_platform.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_provider_http.py` | `tests/unit/test_provider_http.py` | move | offline unit lane |
| `tests/test_provider_lifecycle.py` | `tests/unit/test_provider_lifecycle.py` | move | offline unit lane |
| `tests/test_quality.py` | `tests/integration/test_quality.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_release.py` | `tests/harness/test_release.py` | move | harness checks (CI profile coverage, skills, license, release) |
| `tests/test_runtime_compatibility.py` | `tests/unit/test_runtime_compatibility.py` | move | offline unit lane |
| `tests/test_secret_scanner.py` | `tests/tooling/test_secret_scanner.py` | move | tests of repository tooling scripts |
| `tests/test_service_privacy.py` | `tests/integration/test_service_privacy.py` | move | real PostgreSQL/pgvector/Neo4j lane (marker integration); testing.md layout |
| `tests/test_site_experience_contract.py` | `tests/contract/test_site_experience_contract.py` | move | contract lane (oasdiff, schema examples) |
| `tests/test_skills.py` | `tests/harness/test_skills.py` | move | harness checks (CI profile coverage, skills, license, release) |
| `tests/test_visitor_privacy.py` | `tests/unit/test_visitor_privacy.py` | move | offline unit lane |
| `tests/test_web_accounting.py` | `tests/unit/test_web_accounting.py` | move | offline unit lane |
| `tests/test_web_budget.py` | `tests/unit/test_web_budget.py` | move | offline unit lane |
| `tests/test_web_context.py` | `tests/unit/test_web_context.py` | move | offline unit lane |
| `tests/test_workflow.py` | `tests/unit/test_workflow.py` | move | offline unit lane |

## Docs regrouped by Diataxis, ADRs and evidence archive

Motive: about 80 documents without hierarchy and 46 dated reports mixed with living docs (audit P1). Dated evidence moves to `docs/evidence/archive/2026-10/` with an index; links are fixed by lychee in the same PR.

| From | To | Action | Motive |
|---|---|---|---|
| `docs/adrs/001-dependency-direction.md` | `docs/decisions/001-dependency-direction.md` | move | MADR 4 location docs/decisions/NNNN-title.md (ecosystem 14.2); add Confirmation section; ADR 0007 gap recorded in index |
| `docs/adrs/002-shared-kvm4-origin.md` | `docs/decisions/002-shared-kvm4-origin.md` | move | MADR 4 location docs/decisions/NNNN-title.md (ecosystem 14.2); add Confirmation section; ADR 0007 gap recorded in index |
| `docs/adrs/003-production-ownership.md` | `docs/decisions/003-production-ownership.md` | move | MADR 4 location docs/decisions/NNNN-title.md (ecosystem 14.2); add Confirmation section; ADR 0007 gap recorded in index |
| `docs/adrs/004-current-public-knowledge.md` | `docs/decisions/004-current-public-knowledge.md` | move | MADR 4 location docs/decisions/NNNN-title.md (ecosystem 14.2); add Confirmation section; ADR 0007 gap recorded in index |
| `docs/adrs/005-project-postgres-consolidation.md` | `docs/decisions/005-project-postgres-consolidation.md` | move | MADR 4 location docs/decisions/NNNN-title.md (ecosystem 14.2); add Confirmation section; ADR 0007 gap recorded in index |
| `docs/adrs/006-canonical-adapters.md` | `docs/decisions/006-canonical-adapters.md` | move | MADR 4 location docs/decisions/NNNN-title.md (ecosystem 14.2); add Confirmation section; ADR 0007 gap recorded in index |
| `docs/adrs/008-supported-postgres-base.md` | `docs/decisions/008-supported-postgres-base.md` | move | MADR 4 location docs/decisions/NNNN-title.md (ecosystem 14.2); add Confirmation section; ADR 0007 gap recorded in index |
| `docs/agent-skills.md` | `docs/reference/agent-skills.md` | move | Skill catalog reference; regenerated from skills frontmatter |
| `docs/api-contract.md` | `docs/reference/api-contract.md` | move | Reference (Diataxis) |
| `docs/architecture.md` | `docs/explanation/architecture.md` | rewrite | Explanation with C4 level 1-2 Mermaid; absorbs diagrams.md |
| `docs/assistant-evaluation.md` | `docs/reference/evals.md` | rewrite | Rewritten for the two-tier model; the 1000-bank instructions are retired |
| `docs/assistant-voice.md` | `docs/explanation/assistant-voice.md` | move | Explanation |
| `docs/bounded-web-context.md` | `docs/explanation/bounded-web-context.md` | move | Explanation |
| `docs/ci.md` | `docs/reference/ci.md` | rewrite | Reflects classify + profiles + ci-gate |
| `docs/conversation-evaluation.md` | `docs/reference/evals.md` | merge | Multi-turn evaluation folded into the single evals reference |
| `docs/coordination/analytics-direct-edge-v1.md` | `docs/reference/contracts/analytics-direct-edge-v1.md` | move | Cross-repo contract note |
| `docs/coordination/portfolio-assistant-knowledge.md` | `docs/reference/contracts/portfolio-assistant-knowledge.md` | move | Cross-repo contract note |
| `docs/coordination/portfolio-content-layout.md` | `docs/reference/contracts/portfolio-content-layout.md` | rewrite | Add layout-neutral key rule; layout drift is the root cause of the P0 data bug |
| `docs/decisions.md` | `docs/evidence/archive/2026-10/decisions-log-2026-09.md` | archive | Dated decision log superseded by ADRs; links preserved |
| `docs/dependency-updates.md` | `docs/reference/dependency-updates.md` | rewrite | Documents the weekly single-PR rule and daily vulnerability job |
| `docs/deployment-contract.md` | `docs/reference/deployment-contract.md` | rewrite | Add /healthz and /readyz (expand), env schema, entry-point names, digest deploy |
| `docs/deployment.md` | `docs/how-to/deploy-with-vps-ops.md` | move | How-to; vps-ops owns execution |
| `docs/diagrams.md` | `docs/explanation/architecture.md` | merge | Diagrams live with the architecture explanation |
| `docs/docker-layout-handoff.md` | `docs/evidence/archive/2026-10/docker-layout-handoff.md` | archive | Dated handoff |
| `docs/engineering-coordination.md` | `docs/explanation/engineering-coordination.md` | move | Explanation |
| `docs/environment.md` | `docs/reference/environment.md` | rewrite | Generated from Settings env schema; test compares |
| `docs/feedback-and-improvement.md` | `docs/explanation/feedback-and-improvement.md` | move | Explanation; links to the eval promotion flow |
| `docs/frontend-handoff.md` | `docs/reference/frontend-handoff.md` | rewrite | Consumer guide refreshed after contract v1.1 |
| `docs/graph-retrieval.md` | `docs/explanation/graph-retrieval.md` | move | Explanation; adds graph ablation numbers when measured |
| `docs/knowledge-sync.md` | `docs/how-to/maintain-knowledge.md` | move | How-to |
| `docs/live-evaluation-readiness.md` | `docs/evidence/archive/2026-10/live-evaluation-readiness.md` | archive | Dated audit; open findings A1-A9 tracked as GitHub issues and in audit.md |
| `docs/local-analytics-demo.md` | `docs/how-to/local-analytics-demo.md` | move | How-to |
| `docs/local-development.md` | `docs/tutorials/local-development.md` | rewrite | Tutorial: one command to first fixture answer (just demo) |
| `docs/private-observability.md` | `docs/explanation/private-observability.md` | move | Explanation |
| `docs/product-analytics.md` | `docs/reference/product-analytics.md` | move | Reference |
| `docs/quality-pass.md` | `docs/evidence/archive/2026-10/quality-pass.md` | archive | Dated pass |
| `docs/release-checklist.md` | `docs/how-to/release.md` | rewrite | How-to for release-please, promotion PR and post-release checks |
| `docs/runtime-baseline.md` | `docs/reference/runtime-baseline.md` | move | Reference |
| `docs/site-experience-contract.md` | `docs/reference/site-experience-contract.md` | move | Reference |
| `docs/support-policy.md` | `docs/reference/support-policy.md` | rewrite | Align with ecosystem LTS matrix (Python 3.14.x, PG 18, Neo4j 5.26) |
| `docs/synthetic-evaluation-export.md` | `docs/reference/synthetic-evaluation-export.md` | move | Reference |
| `docs/threat-model.md` | `docs/explanation/threat-model.md` | rewrite | Add OWASP LLM Top 10 2025 mapping and red-team coverage |
| `docs/verification/agent-skills.json` | `docs/evidence/archive/2026-10/agent-skills.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/backend-rc.json` | `docs/evidence/archive/2026-10/backend-rc.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/bounded-live-smoke-2026-10-17.md` | `docs/evidence/archive/2026-10/bounded-live-smoke-2026-10-17.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/clean-architecture-2026-10-17.md` | `docs/evidence/archive/2026-10/clean-architecture-2026-10-17.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/common-layout-preflight-2026-10-18.md` | `docs/evidence/archive/2026-10/common-layout-preflight-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/common-layout-results-2026-10-18.md` | `docs/evidence/archive/2026-10/common-layout-results-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/container-security-2026-10-18.md` | `docs/evidence/archive/2026-10/container-security-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/continuity-after.json` | `docs/evidence/archive/2026-10/continuity-after.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/continuity-before.json` | `docs/evidence/archive/2026-10/continuity-before.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/conversations-after.json` | `docs/evidence/archive/2026-10/conversations-after.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/conversations-before.json` | `docs/evidence/archive/2026-10/conversations-before.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/conversations-rc.json` | `docs/evidence/archive/2026-10/conversations-rc.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/database-images-2026-10-10.md` | `docs/evidence/archive/2026-10/database-images-2026-10-10.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/database-queries-2026-10-17.json` | `docs/evidence/archive/2026-10/database-queries-2026-10-17.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/database-queries-2026-10-17.md` | `docs/evidence/archive/2026-10/database-queries-2026-10-17.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/dependency-cohort-2026-10-18.md` | `docs/evidence/archive/2026-10/dependency-cohort-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/embedding-corpus-identity-2026-10-18.md` | `docs/evidence/archive/2026-10/embedding-corpus-identity-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/final-artifact-closeout-2026-10-18.md` | `docs/evidence/archive/2026-10/final-artifact-closeout-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/graph-readiness-2026-10-18.md` | `docs/evidence/archive/2026-10/graph-readiness-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/grounded-current.json` | `docs/evidence/archive/2026-10/grounded-current.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/live-depth-2026-10-10.json` | `docs/evidence/archive/2026-10/live-depth-2026-10-10.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/live-depth-2026-10-10.md` | `docs/evidence/archive/2026-10/live-depth-2026-10-10.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/neo4j-release-blocker-2026-10-17.md` | `docs/evidence/archive/2026-10/neo4j-release-blocker-2026-10-17.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/neo4j-vendor-refresh-2026-10-17.md` | `docs/evidence/archive/2026-10/neo4j-vendor-refresh-2026-10-17.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/overnight-readiness-2026-10-10.md` | `docs/evidence/archive/2026-10/overnight-readiness-2026-10-10.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/paired-ci-profile-2026-10-18.md` | `docs/evidence/archive/2026-10/paired-ci-profile-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/postgres-startup-2026-10-18.md` | `docs/evidence/archive/2026-10/postgres-startup-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/postgres-supported-base-2026-10-18.md` | `docs/evidence/archive/2026-10/postgres-supported-base-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/postgres18-2026-10-12.md` | `docs/evidence/archive/2026-10/postgres18-2026-10-12.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/private-observability-2026-10-12.md` | `docs/evidence/archive/2026-10/private-observability-2026-10-12.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/product-analytics-v2-2026-10-18.md` | `docs/evidence/archive/2026-10/product-analytics-v2-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/project-postgres-2026-10-17.md` | `docs/evidence/archive/2026-10/project-postgres-2026-10-17.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/provider-transport-2026-10-17.md` | `docs/evidence/archive/2026-10/provider-transport-2026-10-17.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/question-coverage.json` | `docs/evidence/archive/2026-10/question-coverage.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/readme-captures-2026-10-12.md` | `docs/evidence/archive/2026-10/readme-captures-2026-10-12.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/readme-gallery.md` | `docs/evidence/archive/2026-10/readme-gallery.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/retrieval-after.json` | `docs/evidence/archive/2026-10/retrieval-after.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/runtime-2026-10-10.md` | `docs/evidence/archive/2026-10/runtime-2026-10-10.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/runtime-compatibility-2026-10-17.md` | `docs/evidence/archive/2026-10/runtime-compatibility-2026-10-17.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/runtime-security-2026-10-10.md` | `docs/evidence/archive/2026-10/runtime-security-2026-10-10.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/site-experience-contract-2026-10-18.md` | `docs/evidence/archive/2026-10/site-experience-contract-2026-10-18.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/skill-discovery-2026-10-18.json` | `docs/evidence/archive/2026-10/skill-discovery-2026-10-18.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/toolchain-security-2026-10-17.md` | `docs/evidence/archive/2026-10/toolchain-security-2026-10-17.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/ux-release.json` | `docs/evidence/archive/2026-10/ux-release.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/web-context-2026-10-13.json` | `docs/evidence/archive/2026-10/web-context-2026-10-13.json` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/verification/web-context-2026-10-13.md` | `docs/evidence/archive/2026-10/web-context-2026-10-13.md` | archive | Dated verification record; moved out of the living docs tree, indexed in docs/evidence/README.md |
| `docs/vps-ops-request.md` | `docs/evidence/archive/2026-10/vps-ops-request.md` | archive | Dated request; deploy contract is the living doc |

## Evals regrouped

Motive: one golden set and one full set (owner decision), harness outside the shipped package, legacy bank frozen under `evals/archive/`, result artifacts treated as evidence.

| From | To | Action | Motive |
|---|---|---|---|
| `evals/assistant-intents.json` | `evals/archive/legacy-2026-10/assistant-intents.json` | archive | Canonical authored intents (100 families) kept for provenance after distillation. Copied in M2-4 part 2; the original stays until `scripts/build_assistant_bank.py` and `tests/test_grounded_assistant.py` read the archive (follow-up) |
| `evals/assistant.json` | `evals/archive/legacy-2026-10/assistant.json` | archive | 1000-case generated bank (670 dev + 330 holdout); source for distillation of golden and full tiers, then frozen. Copied in M2-4 part 2; the original stays until `scripts/evaluate_assistant.py`, `scripts/build_assistant_bank.py --check` and `tests/test_grounded_assistant.py` read the archive (follow-up) |
| `scripts/evaluate_conversations.py` (`SCENARIOS`, `CONTINUITY_SCENARIOS`) | `evals/archive/legacy-2026-10/scenarios.json` | archive (extract) | 16 scripted legacy scenarios frozen as data for the full tier; the script stays (it is the runner) |
| `evals/fixture-results.json` | `(deleted)` | delete | Generated result artifact; reports go to artifacts/ and ratchet files |
| `evals/live-depth-2026-10-10.json` | `docs/evidence/archive/2026-10/evals/live-depth-2026-10-10.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/live-depth-final-2026-10-10.json` | `docs/evidence/archive/2026-10/evals/live-depth-final-2026-10-10.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/live-depth-revalidation-2026-10-10.json` | `docs/evidence/archive/2026-10/evals/live-depth-revalidation-2026-10-10.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/live-role-final-2026-10-10.json` | `docs/evidence/archive/2026-10/evals/live-role-final-2026-10-10.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/retrieval.json` | `evals/retrieval/queries.jsonl + evals/retrieval/qrels.jsonl` | rewrite | P0: expected paths still use retired src/content layout (hybrid 2/9 on new layout, 8/9 on old); rebuilt as layout-neutral qrels |
| `evals/voice-2026-10-12.json` | `docs/evidence/archive/2026-10/evals/voice-2026-10-12.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/voice-final-2026-10-12.json` | `docs/evidence/archive/2026-10/evals/voice-final-2026-10-12.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/web-context-2026-10-13.json` | `docs/evidence/archive/2026-10/evals/web-context-2026-10-13.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/web-context-cache-revalidation-2026-10-13.json` | `docs/evidence/archive/2026-10/evals/web-context-cache-revalidation-2026-10-13.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/web-context-continuity-revalidation-2026-10-13.json` | `docs/evidence/archive/2026-10/evals/web-context-continuity-revalidation-2026-10-13.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/web-context-final-revalidation-2026-10-13.json` | `docs/evidence/archive/2026-10/evals/web-context-final-revalidation-2026-10-13.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/web-context-metrics-revalidation-2026-10-13.json` | `docs/evidence/archive/2026-10/evals/web-context-metrics-revalidation-2026-10-13.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `evals/web-context-revalidation-2026-10-13.json` | `docs/evidence/archive/2026-10/evals/web-context-revalidation-2026-10-13.json` | archive | Dated live-run result artifact (2026-10); evidence, not a living eval input |
| `scripts/build_assistant_bank.py` | `evals/harness/distill.py` | replace | Generator of the retired 1000-case bank replaced by a one-shot distillation tool that writes golden and full sets; then removed |
| `scripts/evaluate_assistant.py` | `evals/harness/run_full.py` | rewrite | Runner for the full tier; shares graders with the golden runner; remote-Neo4j isolation gap A1 closed |
| `scripts/evaluate_conversations.py` | `evals/harness/multi_turn.py` | rewrite | Multi-turn scenarios become golden/full multi-turn items on the same runner |
| `scripts/evaluate_retrieval.py` | `evals/harness/retrieval.py` | rewrite | Recall@k/nDCG/MRR with ranx over qrels; layout-neutral gold keys (P0) |
| `scripts/evaluation_isolation.py` | `evals/harness/isolation.py` | move | Eval isolation guard stays fail-closed; validates both databases |

## CI, containers and skills

Motive: ecosystem sections 5, 6, 8 and 15.1.

| From | To | Action | Motive |
|---|---|---|---|
| `.agents/skills/api-change-storage` | `.agents/skills/api-change-storage/ (real directory)` | replace | Symlink direction inverted: directory becomes canonical, .claude/skills/<name> links to it |
| `.agents/skills/api-change-stream` | `.agents/skills/api-change-stream/ (real directory)` | replace | Symlink direction inverted: directory becomes canonical, .claude/skills/<name> links to it |
| `.agents/skills/api-change-use-case` | `.agents/skills/api-change-use-case/ (real directory)` | replace | Symlink direction inverted: directory becomes canonical, .claude/skills/<name> links to it |
| `.agents/skills/api-maintain-knowledge` | `.agents/skills/api-maintain-knowledge/ (real directory)` | replace | Symlink direction inverted: directory becomes canonical, .claude/skills/<name> links to it |
| `.agents/skills/api-verify-release` | `.agents/skills/api-verify-release/ (real directory)` | replace | Symlink direction inverted: directory becomes canonical, .claude/skills/<name> links to it |
| `.claude/skills/api-change-storage/SKILL.md` | `.agents/skills/api-change-storage/SKILL.md` | move | Canonical location is .agents/skills (ecosystem 15.1, PAA-D13); .claude/skills/<name> becomes a relative symlink; add evals/triggers.json and evals/evals.json |
| `.claude/skills/api-change-stream/SKILL.md` | `.agents/skills/api-change-stream/SKILL.md` | move | Canonical location is .agents/skills (ecosystem 15.1, PAA-D13); .claude/skills/<name> becomes a relative symlink; add evals/triggers.json and evals/evals.json |
| `.claude/skills/api-change-use-case/SKILL.md` | `.agents/skills/api-change-use-case/SKILL.md` | move | Canonical location is .agents/skills (ecosystem 15.1, PAA-D13); .claude/skills/<name> becomes a relative symlink; add evals/triggers.json and evals/evals.json |
| `.claude/skills/api-maintain-knowledge/SKILL.md` | `.agents/skills/api-maintain-knowledge/SKILL.md` | move | Canonical location is .agents/skills (ecosystem 15.1, PAA-D13); .claude/skills/<name> becomes a relative symlink; add evals/triggers.json and evals/evals.json |
| `.claude/skills/api-verify-release/SKILL.md` | `.agents/skills/api-verify-release/SKILL.md` | move | Canonical location is .agents/skills (ecosystem 15.1, PAA-D13); .claude/skills/<name> becomes a relative symlink; add evals/triggers.json and evals/evals.json |
| `.github/ISSUE_TEMPLATE/bug_report.md` | `.github/ISSUE_TEMPLATE/bug.yml + feature.yml + config.yml` | replace | Issue forms, blank issues disabled |
| `.github/dependabot.yml` | `.github/dependabot.yml` | rewrite | multi-ecosystem-groups weekly (uv, github-actions, docker), Monday 09:00 ART, develop, one PR |
| `.github/pull_request_template.md` | `.github/pull_request_template.md` | rewrite | Ecosystem PR template: summary, issue, evidence, docs/agent-docs, risk |
| `.github/workflows/dependency-policy.yml` | `(deleted)` | delete | pull_request_target automation retired (PAA-D14); shared deps-weekly-guard replaces it |
| `.github/workflows/quality.yml` | `.github/workflows/ci.yml + nightly.yml + weekly.yml` | rewrite | classify job and profiles calling engineering-standards reusable workflows by SHA; ci-gate replaces checks; no cross-repo checkouts; build once, attest |
| `infra/compose/local.yaml` | `infra/compose/local.yaml` | rewrite | Runtime hardening snippet (read_only, cap_drop, pids/mem limits), pinned digests, docker-bake.hcl as build entry point |
| `infra/docker/app/Dockerfile` | `infra/docker/api/Dockerfile (targets api and worker)` | rewrite | Canonical Python Dockerfile: BuildKit cache id copied from vps-ops (vps-ops-uv-python314) replaced; git only in worker target; 992 MB image target <= 500 MB (hypothesis: lingua models dominate); labels; SOURCE_DATE_EPOCH |
| `infra/docker/app/Dockerfile.dockerignore` | `infra/docker/api/Dockerfile.dockerignore` | move | Follows Dockerfile; evals/, docs/, tests/ excluded |
| `infra/docker/postgres/Dockerfile` | `infra/docker/postgres/Dockerfile` | rewrite | postgres:18.x-trixie digest + pgvector pg18, same choice as the sibling API |

## Deletions and replacements elsewhere

Motive per row.

| From | To | Action | Motive |
|---|---|---|---|
| `.dockerignore` | `.dockerignore` | rewrite | Exclude evals/, docs/, tests/, artifacts/ |
| `.gitignore` | `.gitignore` | rewrite | Add .mutmut-cache, htmlcov, evals reports |
| `AGENTS.md` | `AGENTS.md` | rewrite | Short; commands equal CI commands (tested); skills list; boundaries |
| `CONTRIBUTING.md` | `CONTRIBUTING.md` | rewrite | Short per ecosystem 14.2; Python style moves to docs/reference/python-style.md |
| `IMPLEMENTATION_STATUS.md` | `(deleted)` | delete | Volatile status prose replaced by CHANGELOG, progress.md and issues; history in git |
| `README.md` | `README.md` | rewrite | Ecosystem README template with measured-results table (golden and full-set numbers, dated) |
| `SECURITY.md` | `SECURITY.md` | rewrite | Ecosystem template: 5-day acknowledgement, private reporting, vulnerability SLA link |
| `docs/master-plan/README.md` | `docs/master-plan/README.md` | rewrite | Master plan v2 replaces v1 in place (changes listed in README) |
| `docs/master-plan/ecosystem.md` | `docs/master-plan/ecosystem.md` | rewrite | Master plan v2 replaces v1 in place (changes listed in README) |
| `docs/master-plan/research/ai-quality.md` | `docs/master-plan/research/ (shared v2 research set)` | delete | v1 research notes superseded by the shared research set; retained in git history, key conclusions carried into plan files |
| `docs/master-plan/research/architecture.md` | `docs/master-plan/research/ (shared v2 research set)` | delete | v1 research notes superseded by the shared research set; retained in git history, key conclusions carried into plan files |
| `docs/master-plan/research/audit-baseline.md` | `docs/master-plan/research/ (shared v2 research set)` | delete | v1 research notes superseded by the shared research set; retained in git history, key conclusions carried into plan files |
| `docs/master-plan/research/ci-cd-supply-chain.md` | `docs/master-plan/research/ (shared v2 research set)` | delete | v1 research notes superseded by the shared research set; retained in git history, key conclusions carried into plan files |
| `docs/master-plan/research/dependencies.md` | `docs/master-plan/research/ (shared v2 research set)` | delete | v1 research notes superseded by the shared research set; retained in git history, key conclusions carried into plan files |
| `docs/master-plan/research/sources.md` | `docs/master-plan/research/ (shared v2 research set)` | delete | v1 research notes superseded by the shared research set; retained in git history, key conclusions carried into plan files |
| `docs/master-plan/research/standards-docs-skills.md` | `docs/master-plan/research/ (shared v2 research set)` | delete | v1 research notes superseded by the shared research set; retained in git history, key conclusions carried into plan files |
| `docs/master-plan/research/testing.md` | `docs/master-plan/research/ (shared v2 research set)` | delete | v1 research notes superseded by the shared research set; retained in git history, key conclusions carried into plan files |
| `docs/master-plan/roadmap.md` | `docs/master-plan/roadmap.md` | rewrite | Master plan v2 replaces v1 in place (changes listed in README) |
| `docs/master-plan/rubrics/README.md` | `docs/master-plan/rubrics.md` | delete | v1 per-lens rubrics replaced by ecosystem rubrics v2 (byte-identical rubrics.md) |
| `docs/master-plan/rubrics/senior-designer.md` | `docs/master-plan/rubrics.md` | delete | v1 per-lens rubrics replaced by ecosystem rubrics v2 (byte-identical rubrics.md) |
| `docs/master-plan/rubrics/senior-developer.md` | `docs/master-plan/rubrics.md` | delete | v1 per-lens rubrics replaced by ecosystem rubrics v2 (byte-identical rubrics.md) |
| `docs/master-plan/rubrics/senior-recruiter.md` | `docs/master-plan/rubrics.md` | delete | v1 per-lens rubrics replaced by ecosystem rubrics v2 (byte-identical rubrics.md) |
| `docs/master-plan/scorecard.md` | `docs/master-plan/scorecard.md` | rewrite | Master plan v2 replaces v1 in place (changes listed in README) |
| `docs/work-checklist.md` | `(deleted)` | delete | Replaced by master-plan progress.md and GitHub issues; volatile status must not live in prose |
| `pyproject.toml` | `pyproject.toml` | rewrite | src layout, ruff families per ecosystem 10.2, mypy strict on src/, import-linter, coverage, dependency groups (dev, eval), console scripts |
| `scripts/check_architecture.py` | `scripts/check_architecture.py` | rewrite | Reduced to the AST rules import-linter cannot express (banned calls, stdlib-only domain); negative fixtures kept; dynamic imports detection kept |
| `scripts/check_workflows.sh` | `(deleted)` | delete | Replaced by shared actionlint + zizmor job |
| `scripts/ci_identity.py` | `(deleted)` | delete | Replaced by build-once image digest, SBOM and provenance in the shared attest workflow |
| `scripts/ci_profile.py` | `(deleted)` | delete | Replaced by classify job and ci-profile.json validated by tests/harness |
| `scripts/dependabot_automation.py` | `(deleted)` | delete | Owner rule: manual merge of one weekly PR; privileged pull_request_target automation retired (PAA-D14) |
| `scripts/dependabot_policy.py` | `(deleted)` | delete | Replaced by shared deps-weekly-guard (PAA-D14) |
| `scripts/image_security.py` | `scripts/image_security.py` | rewrite | Parse Grype JSON (ecosystem default scanner) instead of Trivy; same policy: fail on fixable High/Critical |
| `scripts/validate_skills.py` | `scripts/validate_skills.py` | rewrite | Adds agentskills spec checks, activation-eval bank presence and last-reviewed staleness |

## New files (not in the index because they are not tracked yet)

| Path | Purpose | Milestone |
|---|---|---|
| `justfile` | `just check`, `just demo`, `just eval-golden`, `just eval-full` | M1 |
| `ci-profile.json` | Path map for the classify job (draft in [ci-cd.md](ci-cd.md)) | M1 |
| `standards.lock` | Ecosystem version and workflow SHAs | M1 |
| `.github/workflows/ci.yml`, `nightly.yml`, `weekly.yml` | Call shared reusable workflows | M1 |
| `.github/ISSUE_TEMPLATE/bug.yml`, `feature.yml`, `config.yml`, `.github/CODEOWNERS` | Community files | M3 |
| `SUPPORT.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `release-please-config.json`, `.release-please-manifest.json` | Community and release files | M3 |
| `docker-bake.hcl`, `.hadolint.yaml`, `container-structure-test.yaml` | Container tooling | M1 |
| `.importlinter` (or `[tool.importlinter]`) | Layer contracts | M4 |
| `scorecard/` (Python package) and `scorecard/ratchets/*.json` | scorecard.json aggregator and ratchet baselines | M2 |
| `evals/golden/golden.jsonl`, `evals/golden/README.md`, `evals/schema/*.json` | Golden set and item schema | M2 |
| `evals/full/full.jsonl`, `evals/full/holdout.sealed.jsonl`, `evals/full/manifest.json`, `evals/full/selection.json`, `evals/full/README.md` | Full tier (384 development items + 100 sealed) | M2 |
| `evals/calibration/*.jsonl` | Judge calibration labels (never part of the gate) | M2 (labels from owner) |
| `evals/retrieval/{queries,qrels}.jsonl`, `evals/retrieval/embeddings-<corpus>.npz` | Retrieval qrels and frozen embeddings | M2 |
| `evals/attacks/attacks.jsonl` | 60 deterministic attacks | M2 |
| `evals/cassettes/<prompt_version>/*.jsonl` | Provider-port recordings | M2 (recording needs spend approval) |
| `evals/baselines/*.json` | Metric ratchets | M2 |
| `evals/harness/` | Runner, graders, loaders, distiller, ranx report | M2 |
| `evals/corpus/<snapshot_id>/` | Frozen public corpus snapshot (PAA-D2, owner decision) | M2 |
| `src/portfolio_assistant/prompts/*.md`, `prompts.lock` | Versioned prompts | M2 |
| `tests/{unit,integration,contract,architecture,evals,harness,tooling,property,load,e2e}/` | Lanes | M2 |
| `docs/{tutorials,how-to,reference,explanation,decisions,evidence}/` indexes | Diataxis | M3 |
| `.agents/skills/<name>/` for the catalog skills (implement-task, review-change, verify-release, update-dependencies, write-adr, resume-refactor, score-repo, evaluate-assistant, change-prompt, refresh-contract, api-refresh-corpus) with `evals/{triggers,evals}.json` | Standard skill catalog and activation evals (ecosystem 15.5) | M1 to M3 |
| `.claude/settings.json`, `.claude/hooks/{format,guard-files,guard-bash,fast-check}`, `.claude/agents/{test-runner,reviewer,architecture-reviewer,eval-runner}.md` | Claude Code harness (ecosystem 15.6) | M1 |
| `.codex/config.toml`, `.worktreeinclude` | Codex harness | M1 |
| `.github/workflows/agent-review.yml` | Second-model PR review | M1 |
