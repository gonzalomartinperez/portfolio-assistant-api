# Progress log

Milestone log updated at milestones (ecosystem 3A); the In-flight table is updated on every task merge. A new session reads [RESUME.md](RESUME.md) first, then this file, then runs the resume command (RESUME.md section 3) and continues with the first `todo` row of [roadmap.md](roadmap.md) or the in-progress task below.

## Current state

| Field | Value |
|---|---|
| Current milestone | M1 (foundation) complete on `develop`, all eleven tasks merged (2026-11-14); awaiting the orchestrator's verification and tag `checkpoint/M1` (not tagged by the repo lead) |
| Date | 2026-11-14 |
| `develop` SHA at M1 end | `1be2848` (PR #162); M1 start was `a9d858c` |
| Last tag | `checkpoint/M0` |
| **Next item** | **M2-16: embeddings snapshot (first task of M2), then M2-1 test lanes (roadmap M2)** |
| `engineering-standards` (E1) | Consumed at **v1.0.0** (`1f33be4`): classify, ci-gate, security, deps-weekly-guard, vuln-daily, scorecard and harness assets. Pins are bumped by the weekly dependency PR |
| Known issues | P0-1 fixed (M1-1). P0-2 reproduced on the current corpus, tracked in issue #152 (golden abstention item M2-4, experiment M2-5). P0-3 not reproducible in CI (fixture settings; test kept). P0-4 fixed (weekly group plus guard, M1-6). P0-5 fixed (cache id, M1-4). P0-6 open (holdout sealing, M2-4). Image: api 564.6 MB, worker 663.0 MB, ratchet in `infra/docker/app/image.json`; the 500 MB budget needs the lingua decision (M2-4). Local WSL only: `test_sigterm_replay_unwinds_external_fixture_cleanup` times out (green in CI) |
| Owner toggles pending (input 2, `docs/reference/repo-settings.md`) | Switch the required check from `Required checks` to `ci-gate` (then remove the alias job); secret scanning and push protection; CodeQL default setup; require full-SHA pinning; merge commits only; delete head branches; immutable releases before M7 |
| Pending owner decisions | Owner inputs only (exactly three, same as README and RESUME): (1) PAA-D5 20% spot check of bootstrapped judge labels (DR-05); (2) release approvals: M7 promotion and the M1-8 GitHub settings checklist; (3) MV VPS purchase. Everything else, including spend within DR-04 caps, is delegated |

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

Resume: `git log --oneline --grep 'M1-'`, `gh pr list --state all --search 'M1-'`, then the first `todo` row of roadmap.md.

## Ecosystem status table (nine rows, copy; updated only at milestones; a drift check compares copies)

| Repo | Plan v2 | Milestone reached | Default/integration branch SHA (`develop`; `main` for main-only repos) | Note |
|---|---|---|---|---|
| portfolio | written 2026-11-09 | none | `0a1ff56` (`origin/develop`) |  |
| portfolio-assistant-api | written 2026-11-09 | M1 complete, awaiting `checkpoint/M1` | `1be2848` (`origin/develop`) | this repo |
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
