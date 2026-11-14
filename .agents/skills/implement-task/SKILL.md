---
name: implement-task
description: "Takes one ready roadmap item through the per-PR pipeline: worktree, tests first, local checks, PR with evidence, review chain, merge on green ci-gate. Use when the user or the orchestrator says \"implement M1-07\", \"do the next roadmap task\" or \"ship this item\", even if no PR is mentioned. Not for reviewing someone else's change (use review-change) or for the weekly dependency PR (use update-dependencies)."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# implement-task

Tools: Read, Grep, Glob, Bash, Edit, Write. This skill does not authorize commits, pushes, merges,
paid calls or deployment; the current task's scope and authority still decide (AGENTS.md).

## Checklist

- [ ] AGENTS.md and the roadmap item with its acceptance criteria read
- [ ] Failing test written at the right layer first
- [ ] `just check` and `just test` green, run through the test-runner agent
- [ ] Review chain finished and every finding answered
- [ ] PR opened into `develop` with What, Why, Evidence, Risk, Rollback

## Procedure

1. Read AGENTS.md, `docs/master-plan/roadmap.md` (the item and its acceptance criteria) and `docs/master-plan/progress.md`.
2. `git fetch` and create a worktree under `../wt/<slug>` on `<type>/<milestone>-<slug>` from `origin/develop`. Never work on `develop` or `main` directly.
3. Write or extend the failing test at the right layer first (`app/domain` pure unit tests, application use cases, adapters, HTTP/SSE contract), then implement. Keep one concern and about 400 changed lines.
4. Run `just check` and `just test` (offline: `uv run pytest -q -m 'not integration'`). Integration needs `TEST_INTEGRATION=1` and isolated Compose projects, ports and databases (`docs/local-development.md`). Fix until green. Fixture mode stays the default; no real API key is read or used.
5. Run the review chain: reviewer agent, Codex second opinion (or the documented fallback), architecture-reviewer for structural changes. Reproduce every finding before acting.
6. Open the PR into `develop` with `.github/pull_request_template.md`. Merge only with current owner authorization, green checks and the required reviews: `gh pr checks <n> --watch`, then `gh pr merge <n> --merge --delete-branch`. Promotion to `main` needs separate explicit approval.
7. Remove the worktree and tick the item in `docs/master-plan/progress.md` when asked to.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

PR URL, CI run URL, merge commit SHA (when authorized), tests added, review findings and how each was answered, fixture versus live verification stated separately.
