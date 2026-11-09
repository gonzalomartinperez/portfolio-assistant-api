# Roadmap M0 to M8 and MV

Milestones are the ecosystem safe points of ecosystem section 3A. A milestone is reached only when `develop` is green on the full `release` CI profile, `progress.md` is updated, the annotated tag `checkpoint/M<n>` is pushed on `develop`, and the ecosystem tracker row is recorded. Everything lands through short task branches, PRs into `develop` and a green `ci-gate`; `main` changes only at M7 (no hotfix before M7, DR-01). Merge command: `gh pr checks --watch && gh pr merge`, merge commits, never squash. **Scorecard acceptance (every milestone):** `scorecard.json` axes at or above the forecast of scorecard.md section 8 (nearest column at or before the milestone), or evaluator-scored at or above it. **Status values:** `todo`, `in-progress`, `done (PR #, SHA)`; update the row and progress.md in-flight table on every task merge. **Resume:** `git log --oneline --grep 'M<n>-'`, `gh pr list --state all --search 'M<n>-'`, then the first `todo` row (RESUME.md section 3).

Execution follows ecosystem 15A: tasks are one concern per PR, branch `<type>/<milestone>-<slug>` from fresh `origin/develop`, target at most 400 changed lines excluding generated files and snapshots; **move-only PRs** (test lanes M2-1, docs reorganization M3-2, `src` rename M4-4) carry no behaviour change and are exempt from the size target because git records them as renames, and they are reviewed by checking that content is unchanged (rename similarity) and the gate is green. A task failing CI or review three times is parked with a diagnosis note. Owner touchpoints are exactly the three inputs of README section 7 (judge-label spot check, release approvals including the GitHub settings checklist, MV VPS purchase) plus the weekly Dependabot PR merge and one short report per milestone; spend within the DR-04 caps needs no one.

Phases (template mapping): **A** polish (M1 to M3), **B** architecture and typing (M4), **C** end state (M5 to M7), **V** VPS-gated (MV). Effort: S under 8 agent-hours, M 8 to 30, L over 30; hours are agent work, with several agents in parallel (worktrees), so wall-clock is a fraction. Owner touchpoints are marked **[owner]**; spend within the DR-04 caps is pre-authorized, exceeding a cap needs the owner.

## Parallel streams (what can run at the same time)

| Stream | Content | Starts | Depends on |
|---|---|---|---|
| A: containers and CI | Dockerfile, bake, profiles, ci-gate, supply chain, Dependabot | M1 day 1 | `engineering-standards` (E1) for shared workflows; until it exists, copy templates and migrate later |
| B: evals | P0 fix, harness, golden, full, retrieval, cassettes | M1 day 1 | none for the P0 fix; agent reviewers and bootstrapped labels (DR-05) |
| C: tests | lanes, coverage, property, mutation, contract, load | after the lane move (M2 first week) | A for services in CI |
| D: docs and skills | README, Diataxis, community files, skills | M3, skills layout at M1 | B for the results table |
| E: typing and refactor | mypy widening, ruff rollout, retrieval pipeline, `src` rename | M3 typing, M4 refactor | B baselines and C ratchets must exist first |

## M0: plans merged

Effort S (2 h, sum of rows). Acceptance: this plan is on `develop`; v1 history stays in git; owner has the decisions list.

| # | Item | Acceptance | Effort | Status |
|---|---|---|---|---|
| M0-1 | Docs-only PR from `docs/master-plan-v2` replaces `docs/master-plan/` (v1 removed, v2 added) | PR merged with green gate; README contains "Changes from v1" | S, 1 h | todo |
| M0-2 | `progress.md` committed, tag `checkpoint/M0` | tag visible; progress table nine rows | S, 0.5 h | todo |
| M0-3 | Owner is informed of the delegated resolutions (PAA-D2, D4, D5, D9, D12, D15) and of the three owner inputs | README section 7 lists them | S, 0.5 h | todo |

## M1: foundation (Phase A)

Effort L (64 h, sum of rows). Cross-repo: `engineering-standards` repo and shared workflows (E1), pequeverso-assistant-api (same CI and container templates), vps-ops (image targets and health aliases are announced, applied at M4).

| # | Item | Acceptance (measurable) | Effort | Status |
|---|---|---|---|---|
| M1-1 | **P0-1 fix**: layout-neutral `canonical_key`, rebuilt retrieval cases as qrels with canonical keys, test over both layouts | hybrid result on current portfolio layout equals the old-layout result (8/9 or better); property test canonical_key round trip passes; ADR 0012 | S, 6 h | todo |
| M1-2 | Reproduce P0-2 and P0-3 in CI conditions; close P0-3 (fixture or assertion), file P0-2 as the first golden abstention item with an issue | integration lane green on the frozen test corpus, or each failure has a reproduction and an issue; no test loosened | S, 6 h | todo |
| M1-3 | `ci.yml` with `classify`, `ci-profile.json`, `ci-gate` replacing `checks`; `tests/harness/test_ci_profile.py` | every tracked file in a profile; docs-only PR runs only docs jobs; required check renamed with a transition PR | M, 8 h | todo |
| M1-4 | Canonical Dockerfile with `api` and `worker` targets, `docker-bake.hcl`, cache id `portfolio-assistant-api-uv-py314`, labels, `.dockerignore`, hadolint, dockle, container-structure-test, Grype | image at most 500 MB (ratchet) or the lingua measurement recorded with the accepted size; 0 fixable High; structure tests green; ADR 0017 | M, 10 h | todo |
| M1-5 | Image spike: size breakdown by layer, `lingua` share | numbers in `docs/evidence/` | S, 3 h | todo |
| M1-6 | Dependabot weekly rule: wait for `engineering-standards` sandbox proof (E2), then rewrite `dependabot.yml`, delete `dependency-policy.yml`, `dependabot_automation.py`, `dependabot_policy.py` and their tests, enable `deps-weekly-guard` | one grouped PR observed or simulated; guard test; ADR 0019; disabling security-update PRs is a settings toggle on the M1-8 checklist **[owner]** | M, 6 h | todo |
| M1-7 | Security workflows: zizmor, actionlint, gitleaks, CodeQL default setup, dependency-review, Scorecard, osv daily job; pin policy | zizmor 0 high; CodeQL on; Scorecard baseline recorded | M, 8 h | todo |
| M1-8 | Record live repository settings in `docs/reference/repo-settings.md` and list owner toggles (secret scanning, push protection, immutable releases, CodeQL, rulesets, GitHub App for release-please) | file merged; toggles handed to the owner as one checklist (input 2), pending toggles listed and the dependent criteria marked unmet | S, 2 h | todo |
| M1-9 | Harness (ecosystem 15.6): skills layout inversion with symlinks, `.claude/settings.json`, hooks, agents (`test-runner`, `reviewer`, `architecture-reviewer`, `eval-runner`), `.codex/config.toml`, `.worktreeinclude`, `agent-review.yml`; `justfile` (`check`, `demo`, `eval-golden`); AGENTS.md at most 200 lines with its command test; PR template; CODEOWNERS | `just check` equals the CI static job; skills validator green | M, 8 h | todo |
| M1-10 | `psycopg` LGPL exception ADR; dependency table verified with `check_license` and deps.dev | ADR merged; table corrected | S, 2 h | todo |
| M1-11 | Add `/healthz` and `/readyz` (expand) and entry-point console scripts alongside the old forms | contract tests green; old forms unchanged | S, 5 h | todo |

Exit: develop green on the release profile; scorecard acceptance (D-axes at the M0 column or better, P6/D4/D5 improving); checkpoint/M1. Risks: the shared repo may lag (fallback: local copies of templates, migrate by SHA later); the Dependabot proof may fail on point (1) (supersede flow); image slimming may conflict with the language-detector accuracy (accept measured size).

## M2: quality net (Phase A)

Effort L (159 h = 147 h rows + 12 h PAA-M2-X, across five parallel streams). Cross-repo: pequeverso-assistant-api (harness layout and schema parity), portfolio (corpus layout stability, permission to copy approved public content), owner (20% spot check only).

| # | Item | Acceptance | Effort | Status |
|---|---|---|---|---|
| M2-16 | Embeddings snapshot, first task of M2 (day 1), pre-authorized by DR-04 (PAA-D4, USD 0.05 cap) | semantic lane baseline committed | S, 2 h | todo |
| M2-1 | Move tests into lanes (mechanical Codex task) | all lanes listed in testing.md exist; old flat paths gone; coverage unchanged | S, 4 h | todo |
| M2-2 | Frozen public corpus snapshot (PAA-D2, delegated: approved public content may be committed), `scripts/refresh_corpus.py`, manifest; CI stops checking out `portfolio` and `portfolio-backoffice` | CI has no cross-repo checkout; snapshot hash tested; ADR 0016 | M, 8 h | todo |
| M2-3 | Eval harness package: item schema, loader, runner on the real SSE path with isolation guard (A1 closed), 11 graders with unit tests | graders 100% unit-tested; guard rejects remote Postgres and remote Neo4j (tests); ADR 0011 | M, 16 h | todo |
| M2-4 | Distill golden v1 (80) and full (450, holdout 100) with `distill.py`, no-retrieval ablation, manifests; golden reviewed by two independent reviewer agents (no owner review); assistant-experience strata reallocation merged only after the same two-agent review | golden counts per stratum and locale equal the quotas; schema valid; every answer item fails the no-retrieval ablation; holdout hash committed; legacy bank archived | M, 14 h | todo |
| M2-5 | Retrieval harness with ranx, about 150 qrels (labelled by two independent agents, disagreements resolved by a third), lexical and graph lane baseline, ablation report H1 to H5 | `evals/baselines/retrieval.json` committed; EN-ES gap reported; abstention experiment recorded | M, 14 h | todo |
| M2-6 | Prompt registry (`prompts/*.md`, `prompts.lock`, `PromptSpec`), `prompt_version` in logs and reports; ADR 0014 | prompt change without lock update fails a test; ADR 0014 merged | S, 3 h | todo |
| M2-6b | ADR 0021: tracing stays off, no hosted prompt registry (split from M2-6) | ADR 0021 merged and linked from the prompt-registry docs | S, 2 h | todo |
| M2-7 | Cassette recorder and replayer, golden lane in pytest and in profile `assistant-quality`; ADR 0013. Recording campaign pre-authorized by DR-04 (cap USD 2 per campaign, USD 8 per month, separate key, `eval-live` environment) | golden 80/80 in replay and budgets baseline committed; if a cap would be exceeded the run stops and the owner is asked | M, 10 h | todo |
| M2-8 | Attack pack (60) and rails tests | 60 deterministic attacks graded by code; each promoted failure has a rail test | S, 6 h | todo |
| M2-9 | Coverage gates at measured values, diff coverage 90%, tests for 0% modules (`knowledge_watch`, `retention`) and adapters through the integration lane | whole-repo branch coverage at least 80%; adapters at least 70% branch; entry points at least 75% | L, 18 h | todo |
| M2-10 | Property tests (list in testing.md) and one stateful machine | Hypothesis profiles `ci` and `nightly` wired | M, 10 h | todo |
| M2-11 | mutmut spike on Python 3.14; ADR 0023; incremental PR job and weekly full job on the scoped packages | spike result recorded; first scores baselined as ratchet (no gate below break 60 yet in warn mode, at most 14 days) | M, 8 h | todo |
| M2-12 | Contract lane: oasdiff, Schemathesis (PR short, nightly long), SSE conformance, schema example tests, cross job design | oasdiff blocks a planted breaking edit; Schemathesis runs | M, 10 h | todo |
| M2-13 | Load and resilience: Locust SSE with stubbed provider, fault-injection fixtures, security matrix over all routes | nightly numbers within ecosystem budgets or baselined with ADR | M, 12 h | todo |
| M2-14 | `scorecard` package and ratchet files; nightly `scorecard.json` | nightly artifact exists; regression fails the job | M, 8 h | todo |
| M2-15 | Judge calibration scaffolding only: review interface (`evals-skills:build-review-interface`) and label schema; label bootstrap and validation are deferred to M6-3 | interface and schema committed; judge not gated | S, 2 h | todo |

Exit: scorecard acceptance (axes at the M2 forecast); nightly `scorecard.json`; no gate in warn mode older than 14 days; golden 100% in cassette replay; checkpoint/M2. Risks: a DR-04 cap reached during recording (stop and ask); mutmut 3 on 3.14 may fail (alternatives); distillation quality depends on the reviewer agents (disagreement rate recorded).

## M3: Phase A polish

Effort L (53 h, sum of rows). Cross-repo: portfolio (README results table link), vps-ops (image size note).

| # | Item | Acceptance | Effort | Status |
|---|---|---|---|---|
| M3-1 | README to the ecosystem template (at most 250 lines, results table generated), C4 diagrams, gallery in light and dark | README heading check green; table generated from `scorecard.json` | M, 8 h | todo |
| M3-2 | Docs reorganization into Diataxis, ADRs to `docs/decisions/` with index, dated evidence to `docs/evidence/archive/2026-10/`, delete `IMPLEMENTATION_STATUS.md` and `work-checklist.md` | lychee 0 broken links; file-moves.md executed | M, 8 h | todo |
| M3-3 | Community files: SUPPORT, CODE_OF_CONDUCT, issue forms, SECURITY template, CHANGELOG and release-please config (dry run), CODEOWNERS | all present; release-please dry run passes | S, 5 h | todo |
| M3-4 | `ruff format` to 100 columns and double quotes (one mechanical PR); ruff families rolled out with a shrinking per-file baseline | formatting PR merged alone; findings count in ratchet | M, 8 h | todo |
| M3-5 | mypy scope widened to `adapters/providers`, `observability`, `neo4j`, `portfolio` (Codex worktree for mechanical annotations) | errors 199 to at most 100; ratchet updated | M, 10 h | todo |
| M3-6 | Skills: map the 5 existing skills into the standard catalog (skills.md section 2: 7 core, 3 API, `api-refresh-corpus`), remove `api-verify-release` once its content has landed, activation evals for all | trigger accuracy recorded; no drop over 10 points | M, 10 h | todo |
| M3-7 | First independent three-lens re-score by an evaluator agent; `docs/evidence/scores/` | judged axes replaced by the evaluator's numbers | S, 4 h | todo |

Exit: scorecard acceptance (M3 forecast, judged axes replaced by the M3-7 evaluator scores); P0 and P1 findings of audit.md closed with evidence (or listed with owner and date); no regression versus M2 ratchets; checkpoint/M3.

## M4: architecture and typing (Phase B)

Effort L (112 h = 72 h rows + 40 h PAA-M4-X). Cross-repo: vps-ops (production.lock PR for entry points, health names and image targets), pequeverso-assistant-api (same guard config and layout), portfolio and backoffice (none: wire contract unchanged).

| # | Item | Acceptance | Effort | Status |
|---|---|---|---|---|
| M4-1 | mypy errors 199 to 0 over all of `src/` (postgres, bootstrap, presentation, remaining) | `mypy --strict src` 0 errors; `files = [...]` list removed | L, 20 h | todo |
| M4-2 | Retrieval pipeline replaces `search` (CC 48), rules in `rules.toml`, per-rule ablation table, evidence sufficiency flag | golden 100%; retrieval ratchet no significant drop; ruff C901 at most 10 everywhere in `src/`; ADR 0015 | L, 20 h | todo |
| M4-3 | Domain purity: portfolio TypeScript parsing to `adapters/portfolio/source_format.py`, fixture answer to providers; `Clock` port | architecture guard: domain and application stdlib-only with TypeScript knowledge absent (grep test); ADR 0022 | M, 10 h | todo |
| M4-4 | `src/portfolio_assistant` rename as one isolated mechanical PR, import-linter contracts, guard reduced, vulture | guards enforce with an empty baseline; negative probes pass; Dockerfile and docs updated; ADRs 0009, 0010 | M, 8 h | todo |
| M4-5 | Entry points under `bootstrap/entrypoints` with console scripts; vps-ops lock PR opened by this plan's agent and merged under vps-ops' own rules | vps-ops compose uses the new commands; deploy-contract doc regenerated; old module names removed in the contract phase | M, 6 h | todo |
| M4-6 | Async cleanup (`asyncio.to_thread` mixing), `langsmith` explicit pin review, `prometheus-client` versus OTel review | `to_thread` count in adapters at most the documented residual; tracing-off test still green | M, 8 h | todo |

Exit: scorecard acceptance (M4 forecast); guards enforce with empty baseline; 0 type errors; contract cross jobs green; checkpoint/M4. Risks: rename churn conflicts with open PRs (freeze window, rename last in the milestone); retrieval refactor regressions (metric gate is the net).

## M5: master design (API and conversational UX, Phase C)

Effort L (41 h = 25 h rows + 16 h PAA-M5-X). Cross-repo: portfolio site and backoffice (consume v1.1 in their own tasks), pequeverso-assistant-api (same problem schema and progress events).

| # | Item | Acceptance | Effort | Status |
|---|---|---|---|---|
| M5-1 | RFC 9457 problem documents with `code`, `retryable`, `retry_after_s`, EN and ES messages (neutral Latin American Spanish), documented and tested | every documented error validates; Schemathesis negative cases green | M, 8 h | todo |
| M5-2 | `run.progress` events behind opt-in; cross job proves current consumers ignore them | consumers compile and pass; ADR 0020 | M, 8 h | todo |
| M5-3 | Contract docs: executable examples, frontend handoff refreshed | schema example tests green | S, 4 h | todo |
| M5-4 | Evaluator scoring of P1 to P6 | each at least 95 or a gap list | S, 3 h | todo |
| M5-5 | Consumer refresh PRs (opened in portfolio and backoffice by their agents) | consumer contract tests green against the new snapshot | S, 2 h here | todo |

Exit: develop green on the release profile; scorecard acceptance (M5 forecast); problem documents and progress events validated by the contract jobs in consumers; checkpoint/M5.

## M6: excellence verified

Effort L (47 h, sum of rows).

| # | Item | Acceptance | Effort | Status |
|---|---|---|---|---|
| M6-1 | Mutation thresholds at target (domain, application, ai, graders) | scores meet the targets in testing.md for two consecutive weekly runs | M, 10 h | todo |
| M6-2 | Neo4j spike (DR-10: run in M4; numbers re-checked here) and ADR 0018, decided by the spike rule (PAA-D12) | graph marginal Recall@5 per kind measured; ADR with numbers | M, 8 h | todo |
| M6-3 | Judge calibration (deferred from M2-15): 160 labels bootstrapped by two independent agents (DR-05), owner 20% spot check (input 1), judge validated (TPR, TNR, kappa thresholds) and added as an extra net | calibration report committed; or "not validated" keeps P3 at the provisional 90 | M, 10 h | todo |
| M6-4 | Full-set baseline run and live golden pass^3 under the DR-04 caps (pre-authorized) | full-set report committed; golden live 80/80 x 3 | S, 4 h | todo |
| M6-5 | Independent three-lens re-score; scorecard on two consecutive nightlies | every axis at least 95, or at least 90 where stated (D7, P3) | S, 4 h | todo |
| M6-6 | MV-R (OD-64): release-candidate image built by the `release` profile with SBOM, provenance and verified digest kept as a CI artifact (no registry push, DR-13); vps-ops registry entry, Coolify config as code, secrets inventory (names only); `/healthz` and `/readyz` and migration contracts verified; full-stack rehearsal on a disposable Ubuntu 26.04 VM (SSE through the proxy, migrations, restore drill, rollback) | Rehearsal green for this repo | M, 8 h | todo |
| M6-7 | OD-09 copy refresh: README, repo description, topics and public-facing assistant copy refreshed to the final state with verified facts and the measured results | Copy matches measured reality; links and facts test green | S, 3 h | todo |

Exit: scorecard acceptance (every axis at least 95, or at least 90 where stated) on two consecutive nightlies; mutation targets met two weekly runs; release-candidate image verified; checkpoint/M6.

## M7: release to main

Effort S (8 h, sum of rows, plus owner approvals). Cross-repo: contract-safe order APIs first (this repo and pequeverso-assistant-api), then backoffices, then sites, then vps-ops pins.

| # | Item | Acceptance | Effort | Status |
|---|---|---|---|---|
| M7-1 | release-please PR merged by the owner; version 1.1.0 | CHANGELOG generated | S, 1 h | todo |
| M7-2 | Promotion PR `develop` to `main`, merge commit, release profile green **[owner]** (input 2) | `main` equals the tested `develop` | S, 2 h | todo |
| M7-3 | Tag, immutable GitHub Release with SBOM; image attested as a CI artifact, GHCR publication only at MV (DR-13) | `gh attestation verify` passes on the digest | S, 3 h | todo |
| M7-4 | Back-merge PR `main` to `develop` and vps-ops `production.lock` PR (digest, version, attestation URL) | merged by their owners | S, 2 h | todo |

Exit: `main` equals the tested `develop`; tag 1.1.0 and immutable release verified; back-merge and vps-ops pin PRs merged; checkpoint/M7.

## M8 (ecosystem): GitHub profile showcase

Not a repository milestone here; after every repo is at M7 this repo contributes its README, results table, topics and description (M6-7) as a showcase reference for the redesigned GitHub profile (OD-08), using only verified facts.

## MV: VPS activation (gated by purchase and spend authorization)

Effort L (36 h = 30 h rows + 6 h PAA-MV-X). Owner: buys and authorizes. vps-ops provisions.

| # | Item | Acceptance | Effort | Status |
|---|---|---|---|---|
| MV-1 | Deploy by digest through vps-ops; `/readyz` reports the release SHA | health and version checks green | S, 6 h | todo |
| MV-2 | Observability: SLO dashboards, burn alerts, online evals on sampled traces (language match, abstention rate, citation present, latency, cost) | alerts fire in a drill; an invented fact pages the owner | M, 10 h | todo |
| MV-3 | Live golden pass^3 on the deployed service, real load at 3 times expected peak | 80/80 x 3; ecosystem load thresholds | M, 8 h | todo |
| MV-4 | Backup restore drill with vps-ops and activation of the assistant on the site (owner decision) | drill passed; owner flips the site flag | S, 6 h | todo |

## Risk register

| Risk | Effect | Mitigation |
|---|---|---|
| DR-04 cap reached or spot check late | P3 stays at 85 (cap reached) or provisional 90 (spot check pending) | Everything else proceeds; scorecard states the cause |
| Owner spot-check time | Judge not validated | Judge excluded from gates; the spot check is one 20% sample once |
| Portfolio content layout changes again during its refactor | Citation paths and corpus identity change | Canonical keys, frozen snapshot, refresh script, layout test |
| Shared standards repo late | M1 slips | Local templates, pin migration later |
| Rename churn | Merge conflicts | Single isolated PR, freeze window |
| Mutation tool incompatibility with 3.14 | M2 item slips | Spike first; alternatives; reduce scope not score |
| Dependabot behaviour differs from the documented one | Rule not enforceable by config alone | Guard supersede flow, ADR |

## Assistant experience v2 tasks (see [assistant-experience.md](assistant-experience.md); included in the milestone effort headers above)

| ID | Task | Files (planned) | Acceptance | Effort | Status |
|---|---|---|---|---|---|
| PAA-M2-X | Test scaffolding: block and event JSON Schemas with examples, validator graders (claims, fundamentos quote, URL allowlist), item-schema extensions (`expected_tools`, `memory_fixture`), memory isolation property tests on a spy port, overhead harness with fake clock, web and retrieval injection fixtures | `contracts/blocks.schema.json`, `contracts/examples/blocks/`, `evals/harness/graders/{claims,fundamentos,urls,tools,memory}.py`, `evals/harness/item_schema.py`, `tests/property/test_memory_isolation.py`, `tests/perf/test_overhead_fake_clock.py`, `evals/fixtures/injection/` | Tests exist and fail for the right reasons; golden reallocation (assistant-quality section 5.1) merged | M, 12 h | todo |
| PAA-M4-X | Ports (`WebSearch`, `MemoryStore`, `RetrievalCache`, `Router`, `Flags`), parallel retrieval with deadlines, `evidence_sufficient`, claims pipeline, graph nodes, snapshot ingestion for the closed web topics, all behind flags default off | `src/portfolio_assistant/application/ports/{web_search,memory_store,retrieval_cache,router,flags}.py`, `ai/graph/`, `ai/claims.py`, `adapters/web/`, `adapters/memory/in_memory.py`, `evals/web_snapshots/` | Golden 100% on cassettes; retrieval ratchet unchanged; overhead p95 <= 150 ms; ADRs 0026, 0027 | L, 40 h | todo |
| PAA-M5-X | Contract v1.x `blocks`, `run.progress`, `capabilities`, memory endpoints (GET, confirm, DELETE), retention job, Store adapter | `presentation/routes/memory.py`, `presentation/blocks.py`, `adapters/memory/postgres_store.py`, `jobs/memory_retention.py`, `contracts/openapi.json`, migration for the store | Contract tests; oasdiff additive; isolation and forget tests green; ADRs 0024, 0025 | M, 16 h | todo |
| PAA-MV-X | Live lane with latency; enable flags one at a time (`progress_events`, `blocks_v2`, `semantic_cache`, `memory`, `web_access`) with 7-day observation | `evals/live/latency.py`, flag runbook in `docs/how-to/` | Under DR-04 caps; rollback by flag | S, 6 h | todo |

Effort check (agent-hours, sum of rows): M0 2, M1 64, M2 159, M3 53, M4 112, M5 41, M6 47, M7 8, MV 36; total 522.

**Critical path** (sequential agent-hours, about 159 h; everything else runs in parallel streams): M0-1 (1) then M1-3 (8) then M2-2 (8) then M2-3 (16) then M2-4 (14) then M2-7 (10) then M2-14 (8) then M3-5 (10) then M4-1 (20) then M4-2 (20) then M4-4 (8) then M5-1 (8) then PAA-M5-X (16) then M6-5 (4) then M7 (8). Wall-clock is dominated by CI waits and review, not by these hours.
