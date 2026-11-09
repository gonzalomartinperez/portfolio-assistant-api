# RESUME: continue the portfolio-assistant-api master refactor from any account

Self-contained. You do not need any chat history. Everything is in git.

## 1. What this is

`portfolio-assistant-api` is the public FastAPI service behind the chat on Gonzalo Martin Perez's portfolio: a bilingual (EN and ES) RAG assistant that answers only from approved public portfolio content, with citations, a Neo4j relationship graph, PostgreSQL 18 with pgvector, an atomic monthly spend cap, and a versioned REST and SSE contract. The VPS is not purchased yet, so nothing here is deployed; vps-ops (private repo) owns deployment.

The **master refactor** (planned 2026-11-09) brings this repo and six sibling repos to a common standard: one aggregate CI gate with dynamic profiles, canonical containers, one weekly Dependabot PR, complete tests, an assistant quality system (a golden set of about 80 questions that must pass 100%, plus a full set of about 450), typed and layered code, and consistent docs. This repo's part is in this folder (`docs/master-plan/`).

## 2. Read order

1. `RESUME.md` (this file)
2. `progress.md`: current milestone, next item, known issues, pending decisions
3. `README.md`: decisions PAA-D1 to PAA-D21, delegated resolutions and the owner inputs still needed
4. `roadmap.md`: milestone tables with task IDs and a Status column; continue with the first `todo` row (resume command in section 3)
5. `assistant-quality.md`: the eval design (read before touching `evals/`, prompts, retrieval or graders)
6. `scorecard.md`, `audit.md`, `target-state.md`, `testing.md`, `ci-cd.md` as needed
7. `ecosystem.md` (the standard for all nine repos) and `rubrics.md`
8. Repo rules that always win: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`

## 3. First commands

```sh
cd ~/projects/github/gonzalomartinperez/portfolio-assistant-api
git fetch -q && git checkout develop && git pull --ff-only
git tag --list 'checkpoint/*'           # last safe point; start at or after it
sed -n 1,40p docs/master-plan/progress.md
uv sync --frozen                         # uv 0.13.1, Python 3.14.x from .python-version
uv run ruff check app tests contracts scripts && uv run ruff format --check app tests contracts scripts
uv run mypy && uv run pytest -q -m 'not integration'
```

After M1 these become `just check`. Integration needs the isolated fixture (see `docs/tutorials/local-development.md` once moved, `docs/local-development.md` before): never point it at shared or production services and never delete volumes you did not create. Work on a task branch named `<type>/<milestone>-<slug>` (types `feat`, `fix`, `chore`, `docs`, `deps`; example `fix/m1-canonical-keys`) from fresh `origin/develop`, open a PR into `develop`, merge only with a green `ci-gate`: `gh pr checks --watch && gh pr merge` (never chain with `;`).

### Resume command (find the true next task, also mid-milestone)

```sh
cd ~/projects/github/gonzalomartinperez/portfolio-assistant-api
git log --oneline --grep 'M[0-9]-' -30            # task IDs (M1-3, PAA-M2-X ...) appear in commit and PR titles
gh pr list --state all --search 'M1-' --limit 30     # repeat per milestone prefix; open PRs mean in-progress
sed -n '/In-flight tasks/,/^## /p' docs/master-plan/progress.md
grep -n '| todo |' docs/master-plan/roadmap.md | head -3   # the first todo row of the lowest open milestone is the next task
```

A task is `done` only with a merged PR; a task with an open PR or a pushed branch is `in-progress`: finish it first. Reconcile `roadmap.md` Status, `progress.md` in-flight table and git before starting anything new.

## 4. Prompt to paste into a new session

```
You are continuing the master refactor of portfolio-assistant-api (repo at
~/projects/github/gonzalomartinperez/portfolio-assistant-api). You have no chat history.
1. Read docs/master-plan/RESUME.md, progress.md, README.md and roadmap.md, then the repo's
   AGENTS.md, CLAUDE.md and CONTRIBUTING.md (repo rules win over the plan).
2. Check out develop at or after the latest checkpoint/M<n> tag and verify the baseline
   commands in RESUME.md section 3.
3. Run the resume command of RESUME.md section 3 and take the first `todo` row of roadmap.md (or finish the in-progress task). Work on a task
   branch, open a PR into develop, delegate mechanical work to a Codex worktree and
   verification to test-runner agents, run an independent reviewer and a second-model
   review before the PR leaves draft, and merge only with a green ci-gate using
   `gh pr checks --watch && gh pr merge`.
4. Never: use --admin, push to develop or main, promote to main (only at M7 with explicit
   owner approval), spend beyond the DR-04 caps or call a paid model outside `eval-live`, commit secrets or raw model answers,
   open evals/full/holdout.sealed.jsonl, run pkill -f, or commit as anyone but
   gonzalomartinperez.
5. After every task merge update the Status column in roadmap.md and the In-flight table in progress.md; at each milestone update progress.md, push the annotated tag checkpoint/M<n> on develop,
   and record the milestone in the ecosystem tracker.
Report in the language the owner used with you; repository documents stay in English.
```

## 5. Owner inputs (exactly three) and standing rules

Owner inputs still needed:

1. PAA-D5: one-time spot check of a 20% sample of the bootstrapped judge labels (DR-05); P3 stays at its provisional floor of 90 until it is done.
2. Release approvals: the M7 promotion `develop` to `main` and the one-time GitHub settings checklist of M1-8 (toggles no agent can set); unset toggles never block work, the dependent scorecard criterion stays unmet.
3. MV: VPS purchase and activation authorization (OD-64; owner steps are purchase, DNS and secret entry only).

Everything else is delegated and decided (README section 7): do not ask. DR-04 pre-authorizes the embeddings snapshot, cassette recording, judge runs and live pass^3 within its caps, so recording, snapshot and judge runs proceed in the `eval-live` environment without asking; only exceeding a cap, a new paid tool or a different provider needs the owner. Standing owner rules that are not pending inputs: no production activation or deploy before MV (DR-13), no hotfix before M7, the weekly Dependabot PR is merged manually by the owner, vulnerability exceptions and ecosystem-standard changes need the owner, and legal or commercial facts are never invented.

## 6. Non-negotiable rules

| Rule | Detail |
|---|---|
| Branch flow | Task branch, PR into `develop`, `ci-gate` green, up to date with base, merge commit (no squash; PR title is a Conventional Commit). `main` only at M7 (no hotfix before M7, OD-11 and DR-01). Never `--admin`; no bypass actors |
| Merge only with green CI | `gh pr checks --watch && gh pr merge`, never `;` |
| Identity | Commits and `gh` only as `gonzalomartinperez`; never the secondary account |
| Secrets | None in git, images, logs, build args or reports; `.env.local` is gitignored; no provider key in agent sessions; raw model answers are never committed |
| Spend | `ALLOW_PAID_AI=false` by default; live and recording workflows run only in the `eval-live` environment under the DR-04 caps of PAA-D9 (pre-authorized; exceeding a cap needs the owner) |
| Eval integrity | Never open or print the sealed holdout; do not tune against its results; golden gate is 100% and is never loosened to pass; quarantine needs an issue, owner and deadline |
| Dependabot rule | Exactly one dependency PR per week for all ecosystems (uv, github-actions, docker), Monday 09:00 America/Argentina/Buenos_Aires, target `develop`; never two open; security-update PRs off, alerts on |
| Contracts | Expand then contract; breaking change needs ADR and `contract-major`; vps-ops `production.lock` updated when image, health, contracts or `infra/docker` change |
| Processes | Never `pkill -f`; kill by verified PID; never stop shared services or remove volumes you did not create |
| Scope | This repo only; do not edit sibling repos or vps-ops; do not use private career material |
| Language | Repo docs in English; assistant-facing Spanish in neutral Latin American Spanish; owner name written exactly "Gonzalo Martin Perez" |
| Hotfixes | None before M7 (OD-11, DR-01); nothing reaches `main` before the M7 release |
| Decision registers | `owner-decisions.md` and `owner-decisions-existing.md` (same folder); never contradict them |
| Evidence | A criterion without evidence (CI run, report, SHA, date) is unmet; ratchets only tighten |
