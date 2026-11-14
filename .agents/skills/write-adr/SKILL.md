---
name: write-adr
description: "Writes a MADR 4 architecture decision record from a decision, with options, consequences and a Confirmation section, and links it from the docs. Use when a decision changes structure, a contract, a dependency, a standard or a policy, or when asked to \"record this decision\", even if the change is small. Not for meeting notes or for changelog entries."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# write-adr

Tools: Read, Grep, Glob, Edit, Write. Writing an ADR does not authorize commits or PRs.

## Checklist

- [ ] Next number found and related ADRs identified
- [ ] MADR 4 sections complete, including Confirmation
- [ ] Links added both ways when superseding
- [ ] Docs map updated; `uv run python -m scripts.validate_skills` unaffected

## Procedure

1. Find the next number in `docs/adrs/` (files are `NNN-title.md`, for example `012-layout-neutral-evidence-keys.md`) and the ADRs this one relates to or supersedes. Read `docs/decisions.md` and `docs/master-plan/owner-decisions.md` for binding decisions.
2. Write `NNN-title.md` in MADR 4: context and problem, decision drivers, considered options, decision outcome, consequences, Confirmation (the test or check that proves compliance).
3. Link both ways when superseding; update `docs/decisions.md` or the README Documentation section where the other ADRs are listed.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

The ADR path and the links added.
