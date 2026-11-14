# ADR023: Scoped mutation testing with mutmut on Python 3.14

Status: accepted (2026-11-14, M2-11, PAA-D19).

## Context and problem

Branch coverage does not prove assertions detect broken policy. The testing plan
requires mutation evidence for budget/privacy/evidence rules, analytics periods,
web policy, answer/run/conversation contracts and retrieval fusion/rules. Python
3.14 compatibility was unproven. The local host has three CPUs and substantial
load; this spike must stay small, offline and free of provider calls.

## Decision drivers

- Add one dev dependency (mutmut 3.8.1 plus its transitive packages: libcst, textual,
  rich, coverage, setproctitle, markdown-it-py, mdit-py-plugins, linkify-it-py, mdurl,
  platformdirs), all permissively licensed; no network access during campaigns.
- Mutate source only, with unit tests and bounded worker/time budgets.
- Preserve required CI checks while introducing measurable, expiring warnings.
- Keep uncertain outcomes visible instead of counting them as kills.

## Considered options

- **mutmut 3.8.1:** added to the dev group by this change; pytest selection,
  per-mutant results and aggregate JSON export; runs offline once locked.
- **cosmic-ray:** configurable execution model, but requires a separate campaign
  setup/dependency and an independent Python 3.14 compatibility spike.
- **mewt:** fallback identified by the mutation-testing skill; unavailable in this
  locked environment and not evaluated here.
- **muton:** the other documented fallback; also not installed or evaluated here.

No compatibility or speed comparison is claimed for the untested alternatives.

## Decision outcome

Use mutmut 3.8.1 with explicit file paths in `[tool.mutmut]`, unit test selection,
`also_copy` for application imports and contract fixtures, and two workers.
The scoped domain files are budget, privacy, evidence, analytics periods and web
policy; application files are answer, runs, conversations and contracts. Retrieval
fusion/rules currently live in the single `app/ai/retrieval.py` module, so that
module is included. No standalone prompt loader or `evals/harness/graders` exists
on this branch; both are skipped until present. Tests are never mutation targets.

### Measured spike

Works on Python 3.14: **yes**, with the existing Python **3.14.8**, mutmut
**3.8.1**, and `fork` isolation. The successful campaign temporarily narrowed
`paths_to_mutate` to `app/domain/budget.py`, `tests_dir` to
`tests/unit/test_operations.py`, and pytest's `-k` selection to
`reservation_covers_bounded_request_and_cutoff`. These restrictions belong to the
spike; the committed configuration restores the complete source scope and the unit tests that exercise
it, excluding integration tests.

```sh
uv run mutmut run --max-children 2 'app.domain.budget.*'
uv run mutmut results
uv run mutmut results --all true
uv run mutmut export-cicd-stats
```

| Measurement | Result |
|---|---:|
| Wall time (`/usr/bin/time -p`, complete successful run) | 92.37 s |
| Generated / measured mutants | 40 / 40 |
| Killed | 24 |
| Survived | 16 |
| Timeout | 0 |
| No tests / skipped / suspicious / interrupted / segfault | 0 each |
| Mutation score | 60.00% |

This is a deliberately narrow budget-test sample, not a full domain score. Its
60% seeds the domain ratchet; application, AI and graders remain explicitly
unmeasured. The budget target is 85%, so surviving mutants require later test
improvements even though the sample reaches the 60% break floor.

Two earlier forkserver attempts (first with the whole unit lane, then the narrowed
budget test) were stopped during stats collection. Switching to `fork` and the
narrow test produced the completed run above. This is an observed local execution
workaround, **not proof of a Python 3.14 forkserver defect**; forkserver remains
unverified and should be retested separately. Each attempt had a 1,200-second
external timeout and was stopped earlier. No full campaign ran locally.

The sandbox's default uv cache is read-only and a temporary empty cache lacks
`uv-build==0.13.1`. Local commands therefore used `UV_CACHE_DIR=/tmp/paa-uv`,
`UV_OFFLINE=1` and `UV_NO_SYNC=1` against the already installed frozen environment.
This is an environment workaround, not a dependency change. Mutmut warns that
`paths_to_mutate` and `tests_dir` are deprecated but accepts both requested keys.

## Consequences

- PR mutation runs only changed scoped Python files (30 minutes); weekly/manual
  runs cover the full configured scope (90 minutes). Both use fixture mode,
  two workers and SHA-pinned actions copied from existing CI.
- The stdlib gate groups individual outcomes from `results --all true`. The JSON
  export exists but has only aggregate counts, so it is retained as corroborating
  evidence rather than used to invent package attribution.
- Score is confirmed kills / all measured outcomes. Timeouts, no-tests, skips and
  errors lower the score; unchecked generated mutants are excluded. The general
  target is 75%, graders and budget math 85%; enforcement is below 60% or the
  measured package ratchet. Ratchets only tighten.
- Warning mode defaults through **2026-11-28 UTC**. On November 29 even `--warn`
  or `MUTATION_MODE=warn` cannot waive a shortfall; `--enforce` acts immediately.
  Invalid or empty evidence fails in every mode.
- Mutation stays outside the shared `ci-gate` until its handling of an
  unclassified PR-only/skipped job is verified. Its independent job can fail
  after grace expiry, but that does not make it a required merge check.
- Full scores, hosted execution and forkserver compatibility remain unverified.
  No fabricated full-package baseline, fallback installation or paid call is
  needed to complete this spike.

## Confirmation

- `tests/tooling/test_mutation_gate.py` exercises parsing, grouping, inconclusive
  outcomes, break/ratchet boundaries, warning expiry, enforcement and changed-file
  selection with pure functions; it never runs mutmut.
- `tests/harness/test_ci_profile.py` preserves the required dependency graph and
  checks the independent PR job plus the scheduled workflow's action pins,
  permissions, worker fixture environment and timeout.
- `tests/mutation-baseline.json` records the exact measured sample and counts.
  CI retains per-mutant text and aggregate JSON artifacts for 14 days.
- [CI documentation](../ci.md#mutation-testing-m2-11) describes operation and the
  limit of the advisory job. Local acceptance is Ruff, formatting, mypy, tooling
  and harness tests, and the architecture guard; it is not hosted-run evidence.

Local acceptance on 2026-11-14: Ruff check, Ruff format check, mypy (39 source
files), architecture and CI-profile guards passed. The complete tooling/harness
command finished with **235 passed, 2 failed** in 264.19 seconds. Both failures
are in the unchanged `tests/tooling/test_analytics_demo.py`: socket creation is
denied by the sandbox (`PermissionError: Operation not permitted`), and the
SIGTERM fixture subprocess exceeds its existing 10-second limit (also reproduced
alone). The cause of that timeout is not established. No tests were skipped or
weakened to obtain acceptance. A separate run of the selected unit lane was
stopped after it stalled following seven tests; only the narrow mutation spike
is verified, not the full campaign or full mutation unit selection. The committed
PR and weekly configuration is therefore unverified end to end: the first hosted run
is the second half of the spike, and a red advisory run is read as "evidence
invalid" (the gate prints that label) rather than as a score. `app/application/
conversations.py` is left out of scope until it has unit-lane tests (it is only
exercised by the integration lane, so every mutant would count as untested). In PR
mode one changed file stands in for its group, so the PR score is an approximation of
the group ratchet; the weekly full run is authoritative.
