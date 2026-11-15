# Progress log

Milestone log updated at milestones (ecosystem 3A); the In-flight table is updated on every task merge. A new session reads [RESUME.md](RESUME.md) first, then this file, then runs the resume command (RESUME.md section 3) and continues with the first `todo` row of [roadmap.md](roadmap.md) or the in-progress task below.

## Current state

| Field | Value |
|---|---|
| Current milestone | M3 (Phase A polish) complete on `develop` (2026-11-15): all seven M3 tasks merged; M2 merged except the parked paid items (M2-16, the M2-7 recording campaign). Awaiting the orchestrator's verification and tag `checkpoint/M3` (`checkpoint/M1` and `checkpoint/M2` are the orchestrator's too; not tagged by the repo lead) |
| Date | 2026-11-15 |
| `develop` SHA at M3 end | `f282add` (PR #196) before this docs PR; M2 start was `1be2848` |
| Last tag | `checkpoint/M0` |
| **Next item** | **M4-1 (mypy 89 to 0, scope widening to all of the app) and M4-2 (retrieval pipeline), once the orchestrator opens M4** |
| `engineering-standards` (E1) | Consumed at **v1.0.0** (`1f33be4`); pins are bumped by the weekly dependency PR (#193 open, owner merges) |
| Known issues | P0-2 closed with evidence (issue #152; `evals/baselines/retrieval.json` abstention sweep: `unsupported_employer_with_evidence` 0); the general no-answer rate (10 of 21 no-answer queries return evidence) moves to M4-2. P0-6 closed (sealed holdout, PR #181). Golden replay is not 80/80 yet because no cassettes are committed (recording is paid, owner). Scheduled workflows (nightly load, mutation weekly, vuln-daily, cross-repo, OpenSSF Scorecard) landed on 2026-11-14 and have no runs yet. Local WSL only: `test_sigterm_replay_unwinds_external_fixture_cleanup` times out (green in CI) |
| Owner toggles pending (input 2, `docs/reference/repo-settings.md`) | Secret scanning and push protection; CodeQL default setup; require full-SHA pinning; immutable releases before M7 (the required check is already `ci-gate` and merges are merge-commit only) |
| Pending owner decisions | (1) PAA-D5 20% spot check of bootstrapped judge labels (DR-05); (2) release approvals: M7 promotion and the repo-settings checklist; (3) MV VPS purchase; plus spend for the parked paid items (M2-16 embeddings snapshot, M2-7 cassette recording campaign) if a spend-authorized run is not delegated |

## Scorecard snapshot at M0 (baseline, rubrics v2; judged axes are planner estimates until the M3 independent evaluator)

| Axis | Score | Axis | Score |
|---|---|---|---|
| D1 Architecture | 82 | P1 Error contract | 78 |
| D2 Code quality | 58 | P2 Streaming UX | 80 |
| D3 Tests | 66 | P3 Assistant message quality | 50 |
| D4 CI/CD | 70 | P4 Contract docs | 80 |
| D5 Security and supply chain | 68 | P5 Consumer consistency | 74 |
| D6 Performance | 62 | P6 Cross-API consistency | 70 |
| D7 Observability | 72 | Recruiter lens | 66 |
| D8 Docs and DX | 64 | | |

Targets: 95 on every axis; floor 90 only for D7 (VPS, until MV) and P3 (provisional until the owner spot check). Details and evidence: [scorecard.md](scorecard.md), [audit.md](audit.md).

## Independent evaluation at M3 (M3-7, 2026-11-15, commit `5ca4647`)

Scores from [docs/evidence/scores/2026-11-15.md](../evidence/scores/2026-11-15.md) (independent evaluator agent, fresh context, did not see planner scores); they replace the judged M0 numbers above.

| Axis | M3 forecast | Evaluator | Gap tasks (owner: repo lead unless marked) |
|---|---|---|---|
| D1 Architecture | 85 | **89** | met |
| D2 Code quality | 82 | 58 | M4-1 (strict mypy 89 to 0), M4-2 (`search` CC 49), M4-4 (vulture), ruff backlog ratchet burn-down (1,572), C901 gate |
| D3 Tests | 92 | 70 | M6-1 (mutation at target, end warn mode), golden replay after the cassette campaign (owner spend), flake report from nightlies |
| D4 CI/CD | 94 | 78 | M6-6 (release-candidate image with SBOM, provenance, digest), M7-3; scheduled workflows accumulate runs |
| D5 Security | 92 | 76 | M6-6 (SBOM and provenance), owner toggles (secret scanning, push protection, CodeQL default setup) |
| D6 Performance | 90 | 50 | `load-nightly.yml` first runs and report (M2-13 follow-up), M4-6 async cleanup |
| D7 Observability | 80 (floor) | 72 | SLOs and inbound `X-Request-ID` propagation (new M4 follow-up), MV for the VPS floor |
| D8 Docs and DX | 92 | 82 | M5-3 (contract docs), M6-7 (copy refresh), first GitHub Release (M7-1, M7-3), one-command fixture demo |
| P1 Error contract | 80 | 55 | M5-1 (RFC 9457, EN and ES messages) |
| P2 Streaming UX | 82 | 76 | M5-2 (`run.progress`), TTFE from the load nightly |
| P3 Message quality | 88 (floor 90 until spot check) | 48 | M2-7 recording campaign (owner spend), M6-3 (judge calibration, owner spot check), M6-4 (live golden pass^3) |
| P4 Contract docs | 94 | 72 | M5-3 (operation descriptions and executable examples) |
| P5 Consumer consistency | 90 | 64 | M5-5 (consumer refresh PRs), first `cross-repo.yml` runs |
| P6 Cross-API consistency | 90 | 70 | M5-1, M4-5 (entry points and health contract phase) |
| Recruiter | 90 | 75 | M6-7, M7-1/M7-3 (release badge), golden replay proof row |

Milestone acceptance rule: M3 is not "reached" by score; this gap list (task IDs above) is the condition for the orchestrator's `checkpoint/M3` decision.

## In-flight tasks (update on every task merge; Status values `todo`, `in-progress`, `done (PR #, SHA)`)

| Task ID | Branch | PR | Status | Notes |
|---|---|---|---|---|
| M0-1 | `docs/master-plan-2026-11` | #140 | done (PR #140, `6766d6a`) | docs-only replacement of `docs/master-plan/` |
| M1 carry-over | `docs/m1-plan-resync` | #144 | done (PR #144, `bb05bef`) | readme-template resync (single-quoted attributes), OD-76 copy, M0 status |
| develop fix | `fix/m1-postgres-fixable-high` | #145 | done (PR #145, `45c6923`) | new fixable HIGH advisories in the Alpine PostgreSQL fixture (krb5-libs, libxslt) |
| M1-1 | `fix/m1-canonical-keys`, `fix/m1-layout-test-ties` | #148, #156 | done (`1aaa0ca`, `9c41993`) | canonical keys, qrels, both-layout integration test, ADR012 |
| M1-2 | `fix/m1-p0-repro-quality-keys` | #154 | done (`b14ebd5`) | P0-2 issue #152; P0-3 not reproducible; evidence `docs/evidence/m1-p0-reproduction-2026-11-14.md` |
| M1-3 | `feat/m1-ci-profiles` | #157 | done (`736f3ff`) | classify + ci-gate (E1 v1.0.0); `Required checks` alias until the owner switches |
| M1-4 | `feat/m1-image-targets`, `chore/m1-image-checks` | #158, #162 | done (`9770548`, `1be2848`) | api/worker targets, bake, hadolint, dockle, structure tests, size ratchet, ADR017 |
| M1-5 | `docs/m1-image-size-spike` | #153 | done (`8734f73`) | `docs/evidence/image-size-spike-2026-11-14.md` |
| M1-6 | `chore/m1-dependabot-weekly` | #159 | done (`45f511b`) | weekly group, guard, policy scripts retired, ADR019 |
| M1-7 | `chore/m1-security-workflows` | #160 | done (`a431468`) | security job, Scorecard, vuln-daily; zizmor 0 high |
| M1-8 | `docs/m1-repo-settings` | #147 | done (`c3c890c`) | `docs/reference/repo-settings.md` with the owner checklist |
| M1-9 | `chore/m1-skills-layout`, `chore/m1-justfile`, `chore/m1-harness-assets` | #150, #151, #161 | done (`e956aa4`, `a507238`, `6b139ee`) | `agent-review.yml` parked (needs an owner-granted provider secret) |
| M1-10 | `docs/m1-psycopg-license-adr` | #146 | done (`a7be65c`) | ADR009, verified licence table |
| M1-11 | `feat/m1-health-entrypoints` | #155 | done (`3025a0d`) | `/healthz`, `/readyz`, console scripts (expand) |

| M2-16 | | | parked | paid embeddings call (DR-04, USD 0.05); the M3 brief forbids paid calls |
| M2-1 | `chore/m2-test-lanes` | #168 | done (`f3cb00b`) | |
| M2-2 | `feat/m2-corpus-snapshot` | #165 | done (`8c48319`) | ADR016 |
| M2-3 | `feat/m2-eval-harness`, `feat/m2-eval-runner` | #170, #171 | done (`f596bcb`, `b2a1673`) | ADR011 |
| M2-4 | `feat/m2-golden-v1`, `feat/m2-full-set` | #173, #181 | done (`27e8ec0`, `93badba`) | sealed holdout (P0-6) |
| M2-5 | `feat/m2-retrieval-harness` | #184 | done (`0ed17bb`) | ranx licences allowed in dependency review (dev-only `eval` group) |
| M2-6, M2-6b | `feat/m2-prompt-registry`, `docs/m2-tracing-adr` | #166, #164 | done (`5c1fef4`, `24b3ec1`) | ADR014, ADR021 |
| M2-7 | `feat/m2-cassettes` | #176 | partial (`7511c8c`) | recording campaign parked (paid, owner) |
| M2-8 | `feat/m2-attack-pack` | #180 | done (`108819a`) | |
| M2-9 | `feat/m2-coverage-gates` | #179 | done (`d3cf6de`) | floors at measured values, diff coverage 90% |
| M2-10 | `feat/m2-property-tests` | #172 | done (`9ea89f6`) | |
| M2-11 | `feat/m2-mutation` | #177 | done (`064a9dc`) | ADR023, warn mode until 2026-11-28 |
| M2-12 | `feat/m2-contract-lane` | #174 | done (`b008399`) | |
| M2-13 | `feat/m2-load-resilience` | #182 | done (`77dbafa`) | ADR024 |
| M2-14 | `feat/m2-scorecard` | #169 | done (`10a6bf3`) | nightly scorecard |
| M2-15 | `feat/m2-judge-scaffolding` | #167 | done (`6a82356`) | |
| M2 fixes | `fix/m2-run-timeout`, `ci/m2-push-concurrency` | #178, #183 | done (`be5e0b0`, `1712b87`) | |
| M3-1 | `docs/m3-readme` | #191 | done (`66090eb`) | results table generated from the scorecard snapshot |
| M3-2 | `docs/m3-diataxis`, `test/m3-doc-links` | #188, #196 | done (`6f3e5f7`, `f282add`) | links test enforces 0 broken links |
| M3-3 | `docs/m3-community-files` | #186 | done (`c549f89`) | release automation per OD-78 |
| M3-4 | `style/m3-ruff-format-100`, `ci/m3-format-only-diff-cover`, `chore/m3-ruff-families` | #194, #192, #195 | done (`8f03851`, `1f4ab7b`, `5ca4647`) | backlog 1,572, ratcheted per family |
| M3-5 | `chore/m3-mypy-scope` | #187 | done (`2e07bbc`) | strict app 202 to 89 |
| M3-6 | `chore/m3-skills-catalog` | #189 | done (`ef205be`) | 15 skills, accuracy 1.00 |
| M3-7 | `docs/m3-progress` | this PR | done | independent evaluator scores |

Resume: `git log --oneline --grep 'M3-'`, `gh pr list --state all --search 'M3-'`, then the first `todo` row of roadmap.md.

## Ecosystem status table (nine rows, copy; updated only at milestones; a drift check compares copies)

| Repo | Plan v2 | Milestone reached | Default/integration branch SHA (`develop`; `main` for main-only repos) | Note |
|---|---|---|---|---|
| portfolio | written 2026-11-09 | none | `0a1ff56` (`origin/develop`) |  |
| portfolio-assistant-api | written 2026-11-09 | M3 complete (M2 paid items parked), awaiting checkpoints | `f282add` (`origin/develop`) | this repo |
| portfolio-backoffice | written 2026-11-09 | none | `e356b13` (`origin/develop`) |  |
| pequeverso | written 2026-11-09 | none | `cbf519c` (`origin/develop`) |  |
| pequeverso-assistant-api | written 2026-11-09 | none | `6912579` (`origin/develop`) |  |
| pequeverso-backoffice | written 2026-11-09 | none | `4d4fb96` (`origin/develop`) |  |
| vps-ops | written 2026-11-09 | none | `f52c3e6` (`origin/main`) | main-only, private |
| pequeverso-marketing | written 2026-11-09 | none | `7d26bf4` (`origin/main`) | main-only, private |
| dropshipping-ops | written 2026-11-09 | none | `8ff0283` (`origin/main`) | main-only, private |

## Milestone log

| Milestone | Date | develop SHA | Scorecard snapshot | What changed | Next item | Known issues | Pending decisions |
|---|---|---|---|---|---|---|---|
| M0 | 2026-11-09 | `6766d6a` (tag `checkpoint/M0`) | see above | v2 plan merged (PR #140) | M1-1 | see above | see above |
| M1 | 2026-11-14 | `1be2848` (tag pending, orchestrator) | not re-scored (scorecard.json arrives with M2-14) | CI profiles and ci-gate, canonical image targets with gates, weekly Dependabot rule, security workflows, harness and skills, health aliases, P0-1/P0-4/P0-5 fixed | M2-16 | P0-2 (#152), P0-6, image budget | owner toggles in repo-settings.md |
| M2 | 2026-11-15 | merged through `0ed17bb` (PR #184) and `b008399` (PR #174) | see the M3 evaluation | test lanes, frozen corpus, eval harness and runner, golden 80 and full 384 + sealed 100, retrieval harness, prompt registry, cassette replayer, attack pack, coverage, property, mutation, contract, load and resilience lanes, scorecard | M3-1 | M2-16 and the M2-7 recording parked (paid) | owner spend for parked items |
| M3 | 2026-11-15 | `f282add` (tag pending, orchestrator) | [scores/2026-11-15.md](../evidence/scores/2026-11-15.md) | README template and results table, Diataxis docs, community files and release automation, ruff 100/double plus family ratchet, strict mypy widened, 15-skill catalog, independent re-score | M4-1 | gap list above | owner toggles and spend |
