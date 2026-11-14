# ADR019: One grouped dependency PR per week, merged manually

Status: accepted (2026-11-14, master plan task M1-6, decision PAA-D14).

## Context and problem

The repository ran three Dependabot ecosystem entries with separate PR limits and a
privileged `pull_request_target` workflow (`dependency-policy.yml`) with two
stdlib scripts that assessed risk and could arm native auto-merge. The owner rule
(OD-22, OD-75) is different: exactly one dependency PR per week for all ecosystems,
target `develop`, green CI, merged manually by the owner, with no per-finding email
noise. Auto-merge conflicts with that rule, and the ecosystem standard forbids the
`pull_request_target` trigger class.

## Decision

1. **Owner rule.** One grouped Dependabot PR per week (Monday 09:00
   America/Argentina/Buenos_Aires), all ecosystems together, against `develop`.
   The owner merges it manually; promotion to `main` is separate.
2. **Mechanism.** `.github/dependabot.yml` follows `templates/dependabot/release.yml`
   of `gonzalomartinperez/engineering-standards` at
   `1f33be46bcb95f42f550f74608bc679cae5575ad` (v1.0.0): one
   `multi-ecosystem-groups` entry `weekly` carrying schedule, `target-branch`,
   `open-pull-requests-limit: 1`, `commit-message` and labels; each `updates` entry
   (`uv`, `github-actions`, `docker` for app and PostgreSQL) joins it with `patterns: ["*"]`.
   Semver cooldowns (7/14/3) apply only to `uv`; other ecosystems use
   `default-days: 7`. The `uv` entry keeps `allow: dependency-type: all` because
   the template does not set it, so Dependabot's default (direct dependencies)
   would silently stop proposing locked transitive updates that the old
   configuration covered. The sandbox did not exercise `allow` inside a group, so
   if Dependabot rejects it the entry is the first thing to remove.
3. **Safety net.** `.github/workflows/deps-weekly-guard.yml`, copied from the shared
   template and pinned to the same SHA, calls the shared reusable workflow. On
   Monday 10:30 ART and on Dependabot PR events it keeps only the newest open
   Dependabot PR (closing an older one with a pointer), records a PR that is behind `develop` in its tracking
   issue without commenting (`request-rebase` stays off, OD-75), and flags a red PR (`needs-fix` plus a tracking issue). It
   never merges.
4. **Security updates.** Dependabot security-update PRs are off and alerts are on
   (owner toggles, already recorded in `docs/reference/repo-settings.md`) because
   security PRs always target the default branch. Critical fixes ride the weekly
   PR; urgent ones use the manual path in `docs/dependency-updates.md`.
5. **Removal.** `dependency-policy.yml`, `scripts/dependabot_automation.py`,
   `scripts/dependabot_policy.py`, `tests/test_dependabot_policy.py` and the CI
   step that audited live controls are deleted, with their py312 lint overrides.

## What the shared sandbox proof established

Source: `docs/decisions/0002-dependabot-weekly-group-sandbox-proof.md` in
`engineering-standards` at `1f33be46bcb95f42f550f74608bc679cae5575ad`.

- Proven: `uv`, `github-actions` and `docker` are accepted in a
  multi-ecosystem group and land in one PR (unverified behavior 3).
- Proven: cooldown applies inside groups for `uv` with 7/14/3 and default days
  elsewhere (behavior 4).
- Proven: group-level `open-pull-requests-limit`, `commit-message`, labels and
  `target-branch: develop` are accepted and honored; security-update PRs stay off
  with alerts on.
- Partly proven (behavior 1): an open group PR is never duplicated in steady
  state (the next run defers to it), but the in-place refresh was not observed.
  Closing the PR makes the next run open one fresh complete PR.
- Not proven (behavior 2): day, time and timezone on groups. They can only be
  observed on a Monday run; the sandbox's final observation was scheduled for
  2026-11-16 12:00 UTC. The first Monday after this config lands on the default
  branch is this repository's own observation.
- The guard was exercised only against a fake API. Its first live runs
  (Dependabot-triggered `pull_request` and the Monday schedule) are part of this
  repository's M1 verification and remain unproven here.
- Not proven for this repository: `allow` inside a group (see Decision 2) and the
  `ignore` rule on `python` inside a group.

Until the in-place refresh is observed, a stale open weekly PR that should pick up
newer versions is closed by the owner and the next run opens a complete one.

## Consequences

- No `docker-compose` entry: Dependabot only parses files named `*compose*.y*ml`
  and the local fixture is `infra/compose/local.yaml`. The Neo4j digest (compose
  fixture, `ci.yml` service, `deploy/neo4j-image.json`) is bumped manually; renaming
  the fixture is a possible later change.

- No privileged workflow or custom merge logic remains; the owner is the only
  merge authority for dependency updates.
- Dependabot config activates only from the default branch, so a `develop`-only
  commit is not live evidence; verify after promotion.
- Up to a week of delay for critical advisories is accepted (OD-22).

## Confirmation

- Shared repository: the guard's tests and the `standards-drift` `dependabot-policy`
  check enforce the shape in every adopter.
- This repository: `tests/test_dependabot_config.py` asserts the group, entry and
  cooldown rules, full Dockerfile and compose directory coverage, and that the
  guard pins the shared workflow by 40-hex SHA with `permissions: {}`.
- Live: observe the first Monday run (one PR, correct time, target `develop`) and
  the first guard run, then record the outcome as an addendum.
