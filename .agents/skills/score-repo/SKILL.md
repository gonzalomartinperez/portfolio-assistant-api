---
name: score-repo
description: "Runs the repository scorecard, compares it with the committed ratchet baselines and assembles the three-lens evidence pack. Use when preparing a milestone safe point or a release, or when asked for the score or quality status of the repo, even if CI is green. Not for fixing the findings."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# score-repo

Tools: Read, Grep, Glob, Bash (read-only). Offline only: never run live or paid evaluations, never set
`ALLOW_PAID_AI=true`, never open `evals/full/holdout.sealed.jsonl`.

## Checklist

- [ ] Rubric and scorecard documents read (`docs/master-plan/rubrics.md`, `scorecard.md`)
- [ ] Evidence collected per axis from CI artifacts and offline commands
- [ ] Any loosening against baselines reported as a finding
- [ ] Criteria without evidence marked unmet

## Procedure

1. Run `just score` (or `uv run python -m scorecard collect` then `check`, see `docs/scorecard.md`); the nightly artifact `scorecard` holds the latest `scorecard.json`. For inputs the package does not collect yet, gather evidence by hand: `just check`, `just test`, and the latest CI run (`gh run view <id>`).
2. Compare each axis with the baseline in `docs/master-plan/scorecard.md`; any loosening of a floor or ratchet is a finding.
3. Collect evidence links per rubric criterion; a criterion without evidence is unmet.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Score per axis, regressions against baselines, evidence links.
