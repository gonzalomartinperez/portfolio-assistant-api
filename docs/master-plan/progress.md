# Progress log

Milestone log updated at milestones (ecosystem 3A); the In-flight table is updated on every task merge. A new session reads [RESUME.md](RESUME.md) first, then this file, then runs the resume command (RESUME.md section 3) and continues with the first `todo` row of [roadmap.md](roadmap.md) or the in-progress task below.

## Current state

| Field | Value |
|---|---|
| Current milestone | M1 (foundation) in progress; M0 reached (PR #140 merged, tag `checkpoint/M0` on `6766d6a`) |
| Date | 2026-11-14 |
| `develop` SHA at M1 start | `a9d858c` (after PR #142 dependency refresh and PR #143 OD-75) |
| Last tag | `checkpoint/M0` |
| **Next item** | **M1-1: P0-1 fix. Layout-neutral `canonical_key` in `domain/portfolio_paths.py`, retrieval cases rebuilt as qrels with canonical keys, test over both portfolio layouts (roadmap M1-1, assistant-quality.md section 3)** |
| `engineering-standards` (E1) | Repository not created yet at M1 start (2026-11-14 02:30 UTC); E1-dependent tasks (M1-3, M1-4 templates, M1-6, M1-7, M1-9) wait up to 3 hours, then use in-repo templates and migrate by SHA later |
| Known issues | P0-1 stale golden retrieval data (hybrid 2/9 on the current portfolio layout); P0-2 `unsupported-employer` retrieves evidence for an absent employer; P0-3 Neo4j vendor-reporting integration test failed in the audit run; P0-4 Dependabot opens several PRs; P0-5 BuildKit cache id copied from vps-ops; P0-6 holdout not sealed (66 of 330 IDs exposed) |
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
| M1 carry-over | `docs/m1-plan-resync` | this PR | in-progress | readme-template resync (single-quoted attributes), OD-76 copy, M0 status |

Resume: `git log --oneline --grep 'M1-'`, `gh pr list --state all --search 'M1-'`, then the first `todo` row of roadmap.md.

## Ecosystem status table (nine rows, copy; updated only at milestones; a drift check compares copies)

| Repo | Plan v2 | Milestone reached | Default/integration branch SHA (`develop`; `main` for main-only repos) | Note |
|---|---|---|---|---|
| portfolio | written 2026-11-09 | none | `0a1ff56` (`origin/develop`) |  |
| portfolio-assistant-api | written 2026-11-09 | M0 (M1 in progress) | `a9d858c` (`origin/develop`) | this repo |
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
