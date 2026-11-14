---
name: verify-release
description: "Verifies a release end to end: release CI profile green, CHANGELOG and version consistent, tag and immutable GitHub Release created, post-deploy checks (build-info SHA, health, version). Use when preparing or checking a develop to main promotion, a release tag or a deploy, even if CI already looks green. Not for day-to-day PRs."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# verify-release

Tools: Read, Grep, Glob, Bash (read-only). This is the generic release checklist. It overlaps the existing
`api-verify-release` skill, which stays for now (merging is a later M3 task); use `api-verify-release` for
scoped backend verification and security review. Never read a promotion check as permission to merge, promote
to `main` or run production; each needs explicit current approval.

## Checklist

- [ ] Promotion PR (`develop` to `main`) ran its CI profile and `ci-gate` is green
- [ ] Release checklist (`docs/release-checklist.md`) items have evidence
- [ ] Contracts exported with no drift; image and manifest evidence recorded
- [ ] Post-deploy checks recorded by the owner of production (vps-ops), not run here

## Procedure

1. Confirm the promotion PR's checks: `gh pr checks <n>`; `ci-gate` must be green.
2. Walk `docs/release-checklist.md`; run `just check` and `just test` and record the results. The release manifest and image checks are in `docs/deployment-contract.md` and `docs/ci.md`.
3. Check the tag and release notes agree with the merge SHA once a release exists. This repository has no CHANGELOG yet; note that gap rather than inventing one.
4. Post-deploy health and build-info comparison are executed by private vps-ops. Record what the owner reports; do not edit vps-ops, install a controller or activate deployment triggers.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

Checklist with evidence links (CI run, release URL, manifest digest), fixture versus live evidence separated, open gaps.
