---
name: implement-task
description: "Takes one ready roadmap item through the per-PR pipeline: worktree, tests first, local checks, PR with evidence, review chain, merge on green ci-gate. Use when the user or the orchestrator says \"implement M1-07\", \"do the next roadmap task\" or \"ship this item\", even if no PR is mentioned. Not for reviewing someone else's change (use review-change) or for the weekly dependency PR (use update-dependencies)."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.1.0"
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
4. Select checks by risk (see Selecting and reading checks), then run `just check` and `just test` (offline: `uv run pytest -q -m 'not integration'`). Integration needs `TEST_INTEGRATION=1` and isolated Compose projects, ports and databases (`docs/local-development.md`). Fix until green. Fixture mode stays the default; no real API key is read or used.
5. Run the review chain: reviewer agent, Codex second opinion (or the documented fallback), architecture-reviewer for structural changes. Reproduce every finding before acting.
6. Open the PR into `develop` with `.github/PULL_REQUEST_TEMPLATE.md`. Merge only with current owner authorization, green checks and the required reviews: `gh pr checks <n> --watch`, then `gh pr merge <n> --merge --delete-branch`. Promotion to `main` needs separate explicit approval.
7. Remove the worktree and tick the item in `docs/master-plan/progress.md` when asked to.

## Selecting and reading checks

Start with `git status --short` and inspect the diff without altering unrelated work. Pick evidence by risk:

| Change | Evidence |
| --- | --- |
| Pure policy (`app/domain`, `app/application`) | targeted unit and `tests/architecture` tests, Ruff, strict mypy |
| HTTP or SSE | `uv run python -m contracts.export` shows no drift, ownership and CSRF tests, incremental delivery and cancellation tests, [frontend handoff](../../../docs/frontend-handoff.md) |
| Persistence or knowledge | real pgvector and Neo4j in the integration lane, concurrency, migration and failed-index recovery; retrieval numbers through evaluate-assistant |
| CI, container or Compose | `bash scripts/check_workflows.sh`, `uv run python -m scripts.validate_compose`, then `uv run python -m scripts.container_smoke --image <ref>`; keep pinned actions, minimal permissions and the `Required checks` aggregate |
| Public contract (`contracts/`, `app/presentation/`) | `uv run pytest -q -m contract`, `uv run python -m scripts.contract_diff --base-sha origin/develop` (needs `oasdiff`), `contract-major` label only for an owner-approved break; see refresh-contract |
| Prompts, retrieval, `app/ai`, graders | `uv run pytest -q tests/evals`, `uv run --group eval python -m evals.harness.retrieval --out artifacts/retrieval-report.json --compare`, `just eval-golden` (exit 3 means re-record, owner-only); see evaluate-assistant and change-prompt |
| Invariants, faults, load | `uv run pytest -q tests/property`, `uv run pytest -q tests/resilience`; load is `uv run --group load python -m tests.load.run_load --profile smoke` |
| Provider HTTP or lifecycle | `uv run pytest -q tests/unit/test_provider_http.py tests/unit/test_provider_lifecycle.py` |
| Security-sensitive | hand the diff to review-change, which delegates to owasp-security-review |

To read a failure, fetch the failing job with `gh run view <id> --log-failed` (or `gh pr checks <n>`) through the
log-analyst agent and quote the first real error, not the tail. Inspect the actual Actions run: a green local
command is not an executed pipeline. The PR also faces coverage floors (`scripts.coverage_gate`, `tests/coverage-floors.json`, diff coverage 90%) and the
advisory mutation job (`scripts.mutation_gate`). A missing service (no Docker) is a recorded gap, never permission to use another
project's database. Fixture tests do not prove model safety, TLS negotiation or VPS capacity. Never bypass a gate or
raise a budget to turn a check green.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

PR URL, CI run URL, merge commit SHA (when authorized), tests added, review findings and how each was answered, fixture versus live verification stated separately.
