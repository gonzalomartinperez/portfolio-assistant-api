# Dependency updates: one weekly PR, merged manually

Rule (owner decisions OD-22 and OD-75, decision PAA-D14, [ADR019](adrs/019-weekly-dependency-pr.md)):
exactly one dependency PR per week, all ecosystems together, green CI, merged by
the owner. No automation approves, arms or merges it.

## Flow

1. Monday 09:00 America/Argentina/Buenos_Aires Dependabot opens one grouped PR
   (`chore(deps): ...`, label `dependencies`) against `develop`, covering `uv`,
   `github-actions` and `docker` (app and PostgreSQL images). The Neo4j image pin
   (`infra/compose/local.yaml`, `ci.yml`, `deploy/neo4j-image.json`) is updated
   manually with its digest: Dependabot cannot parse `local.yaml`. Configuration: `.github/dependabot.yml`; the schedule,
   target branch, PR limit and commit prefix live on the group, not on entries.
2. Cooldowns hold back fresh releases: 7 days by default, and for `uv` 14 days for
   majors and 3 days for patches. Python minor and major image changes are ignored
   and need an explicit project decision.
3. `deps-weekly-guard` (shared `engineering-standards` workflow, pinned by SHA)
   runs Monday 10:30 ART and on Dependabot PR events. It keeps at most one open
   Dependabot PR (the newest; an older one is closed with a pointer), records a PR
   that is behind `develop` in the tracking issue (it does not comment, OD-75), and when CI is red labels the PR
   `needs-fix` and updates one tracking issue.
4. The owner reviews the PR and merges it manually after the required `checks`
   pass. Promotion to `main` stays a separate, explicit decision.

If a red PR needs a fix, push it to the Dependabot branch. That stops Dependabot
rebases for that branch, so to pick up newer versions close the PR and let the
next run (or the guard's supersede flow) open a fresh complete one.

## Alerts and security updates

Dependabot alerts stay on; Dependabot security-update PRs are off (repository
setting, see [repo settings](reference/repo-settings.md)), because they would
target `main` and bypass the weekly PR. The daily vulnerability job (`vuln-daily.yml`, added with M1-7) records findings
silently in one tracking issue; only the Monday summary notifies (OD-75). Alert
emails use GitHub's weekly digest.

## Urgent fixes (manual path)

A critical advisory normally rides the weekly PR. For one that cannot wait, open a
normal task-branch PR into `develop` that bumps only the affected dependency
(`uv lock --upgrade-package <name>` for uv, or the pin in the Dockerfile,
compose file or workflow), with full CI, then merge it manually. The next weekly
PR supersedes or rebases over it. Close the stale weekly PR first if it conflicts.

## Verification and limits

`tests/harness/test_dependabot_config.py` checks the rule offline: one group with the
schedule, target, limit and prefix; every entry joins it; semver cooldowns only
on `uv`; every Dockerfile and compose directory is covered; the guard pins the
shared workflow by full SHA with empty top-level permissions. It cannot prove
live Dependabot behavior; the Monday schedule can only be observed on a Monday
(see the ADR for what the shared sandbox proof established).

The former auto-merge policy workflow and scripts are removed. Repository
auto-merge stays off; no PAT or administrative bypass is used.
