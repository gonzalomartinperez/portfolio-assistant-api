---
name: update-dependencies
description: "Handles the single weekly Dependabot PR: reads the changelogs, fixes breakages on the same branch, keeps ci-gate green and leaves the merge to the owner. Use when the weekly dependency PR is open, labelled needs-fix, or the guard reports it red, even if only one ecosystem broke. Not for urgent single-dependency security fixes (normal task-branch PR) or for merging the PR (owner only)."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# update-dependencies

Tools: Read, Grep, Glob, Bash, Edit, Write. Edits stay on the Dependabot branch; the owner merges.

## Checklist

- [ ] PR body and tracking issue read
- [ ] Changelog read for each major bump
- [ ] `uv.lock` changed only by `uv lock` or Dependabot, never by hand
- [ ] `just check` and `just test` green; `ci-gate` green
- [ ] Merge left to the owner

## Procedure

1. Read the PR body (versions per ecosystem), `docs/dependency-updates.md` and the tracking issue section written by the weekly guard.
2. For each major bump read the upstream changelog and list breaking changes that touch this repo. Check licenses with `uv run python -m scripts.check_license`.
3. Fix breakages on the Dependabot branch in small commits (this stops Dependabot rebases; the guard handles superseding). Use `uv sync --frozen` to reproduce the lock.
4. Run `just check` and `just test`; keep `ci-gate` green. Never merge; the owner merges the weekly PR. Never use a real API key or network service beyond the package index.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Summary for the owner in the PR description: bumps, breaking changes handled, evidence commands and results.
