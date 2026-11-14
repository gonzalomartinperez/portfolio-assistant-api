---
name: review-change
description: "Reviews a diff independently for correctness, security, missing tests and standards compliance, reproducing every finding. Use when asked to \"review this PR\", \"check this diff\", \"second look before merge\", or before committing a non-trivial change, even if the author already reviewed it. Not for writing the fix or for style-only feedback."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# review-change

Tools: Read, Grep, Glob, Bash (read-only commands only). A review never edits files, commits, comments on
GitHub or regenerates contracts unless the task says so.

## Checklist

- [ ] Diff and PR description read; the author's reasoning ignored
- [ ] Correctness, security, data loss, concurrency and contract risks checked
- [ ] Layer rules from AGENTS.md checked (`app/domain` pure; no outward imports)
- [ ] Every finding reproduced or marked unverified
- [ ] Output delivered in the template below

## Procedure

1. Get the diff (`git diff <base>...HEAD` with base `origin/develop`, or `gh pr diff <n>`) and the PR description.
2. Check correctness, security (injection, secrets, authz, ownership/CSRF), data loss (migrations, deletion), concurrency (streaming, cancellation, usage reservations), and that tests exercise the change.
3. Check the repository rules: v1 wire artifacts preserved (`uv run python -m contracts.export` shows no unintended drift), only approved public content in the runtime corpus, no real key or private career-ops material, fixture mode still the default, docs and ADRs updated where behavior changed, Conventional Commit title.
4. Reproduce each finding with a failing test, a command (`uv run pytest -q -m 'not integration' <path>`) or a quoted line; drop what you cannot reproduce or mark it unverified.
5. Report findings by severity (P0 blocks merge, P1 before merge, P2 follow-up) with file:line, scenario and fix.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Findings table (severity, file:line, scenario, fix), then `Confidence: high|medium|low` and `Escalate: yes|no` lines. "no blocking issues" when there are none.
