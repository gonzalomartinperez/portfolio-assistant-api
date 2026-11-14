---
name: resume-refactor
description: "Resumes the master refactor from git alone: reads RESUME.md, the ecosystem tracker and progress.md, checks out the last checkpoint and continues with the first unchecked item. Use when a new session starts on these repositories or when asked \"where were we\" or \"continue the refactor\", even if you remember earlier work. Not for starting new milestones the owner has not opened."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# resume-refactor

Tools: Read, Grep, Glob, Bash (read-only git and gh). Resuming is orientation, not authority: a roadmap or an
earlier session never grants merge, main promotion or production execution.

## Checklist

- [ ] `docs/master-plan/RESUME.md`, `docs/master-plan/owner-decisions.md` and `progress.md` read
- [ ] `develop` state and checkpoint tags checked with git
- [ ] First unchecked item of the current milestone identified
- [ ] Discrepancies between git and the tracker recorded

## Procedure

1. Read `docs/master-plan/RESUME.md`, then `docs/master-plan/owner-decisions.md` (binding), then `docs/master-plan/progress.md` and `docs/master-plan/roadmap.md`.
2. `git fetch --tags`; confirm `origin/develop` is at or after the last `checkpoint/M<n>` tag and that its latest CI run is green (`gh run list --branch develop --limit 5`).
3. Pick the first unchecked item of the current milestone and hand it to implement-task.
4. Never resume from memory or chat history; if git and the tracker disagree, trust git and record the discrepancy.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Current milestone, last checkpoint SHA, next item, blockers.
