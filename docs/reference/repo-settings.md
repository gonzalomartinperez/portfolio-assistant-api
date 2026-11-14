# Repository settings (live record)

Recorded 2026-11-14 from the GitHub REST API (read-only `gh api` calls against
`gonzalomartinperez/portfolio-assistant-api`). This file records the live settings;
it does not change them. Agents cannot change repository settings, so every
difference from the target is an owner toggle in the checklist below (master plan
M1-8, owner input 2). A scorecard criterion that depends on an unset toggle stays
unmet until the toggle is set and this file is updated with the new reading.

Re-read the settings with:

```sh
gh api repos/gonzalomartinperez/portfolio-assistant-api \
  -q '{visibility,default_branch,allow_merge_commit,allow_squash_merge,allow_rebase_merge,delete_branch_on_merge,allow_update_branch,security_and_analysis}'
gh api repos/gonzalomartinperez/portfolio-assistant-api/branches/develop/protection
gh api repos/gonzalomartinperez/portfolio-assistant-api/rulesets
gh api repos/gonzalomartinperez/portfolio-assistant-api/code-scanning/default-setup
gh api repos/gonzalomartinperez/portfolio-assistant-api/immutable-releases
gh api repos/gonzalomartinperez/portfolio-assistant-api/actions/permissions
```

## Live settings

| Area | Setting | Live value (2026-11-14) | Target (master plan) |
|---|---|---|---|
| Repository | Visibility | public | public |
| Repository | Default branch | `main` | `main` (integration branch `develop`) |
| Merging | Merge commit / squash / rebase | allowed / allowed / allowed | merge commit only (ecosystem 3, PR title as Conventional Commit) |
| Merging | Auto-merge | off | off |
| Merging | Delete head branch on merge | off | on |
| Merging | Suggest updating PR branches | off | on |
| Branch protection `develop` | Required check | `Required checks` (job `checks` in `quality.yml`), strict | `ci-gate`, strict (renamed in M1-3 with a transition PR that requires both names) |
| Branch protection `develop` | Enforce for admins | on | on, no bypass actors |
| Branch protection `develop` | Required approvals | 0 | 0 (solo repository; the agent review chain replaces human review) |
| Branch protection `develop` | Force push / deletion | blocked / blocked | blocked / blocked |
| Branch protection `main` | Same as `develop` | same values as `develop` | same as `develop` |
| Rulesets | Branch and tag rulesets | none (classic branch protection only) | rulesets for `develop`, `main` and tags `v*`, applied by the `engineering-standards` script |
| Security | Secret scanning | disabled | enabled |
| Security | Push protection | disabled | enabled |
| Security | Secret scanning validity checks / non-provider patterns | disabled / disabled | enabled / enabled |
| Security | Dependabot alerts | enabled | enabled |
| Security | Dependabot security updates (PRs) | disabled | disabled (OD-22: criticals ride the weekly PR) |
| Security | Private vulnerability reporting | enabled | enabled |
| Security | CodeQL default setup | not configured (languages detected: actions, python) | configured for `actions` and `python` |
| Releases | Immutable releases | disabled | enabled before the first release (M7) |
| Actions | Allowed actions | all | all, with full-SHA pinning required |
| Actions | Require full-SHA pinning | off | on (every workflow already pins full SHAs) |
| Actions | Default `GITHUB_TOKEN` permission | read | read |
| Actions | Actions may approve PR reviews | no | no |
| Environments | `eval-live`, `production` | none exist | `eval-live` (branch restriction, no reviewer, separate provider key, DR-04 caps in code); `production` (owner as required reviewer), created at MV |
| Apps | GitHub App for release-please | none | installed with contents and pull-request scope (E5) before release automation lands |

## Owner checklist (one pass; none of these blocks agent work)

Settings ▸ General:

- [ ] Pull requests: allow merge commits only (untick squash and rebase).
- [ ] Pull requests: tick "Always suggest updating pull request branches".
- [ ] Pull requests: tick "Automatically delete head branches".

Settings ▸ Advanced Security (Code security):

- [ ] Secret scanning: enable, then enable push protection, validity checks and non-provider patterns.
- [ ] CodeQL analysis: "Set up" ▸ Default (languages `actions`, `python`).
- [ ] Keep Dependabot alerts on and Dependabot security updates off (already correct).

Settings ▸ Actions ▸ General:

- [ ] Tick "Require actions to be pinned to a full-length commit SHA".

Settings ▸ General ▸ Releases:

- [ ] Enable immutable releases (any time before M7; needed before the first tag).

Later, when the matching task lands (an agent records the request in the PR):

- [ ] M1-3: when the `ci-gate` transition PR is merged, set `ci-gate` as the required check on `develop` and `main`, then remove `Required checks`.
- [ ] Rulesets: run the `engineering-standards` ruleset script once it exists (E1).
- [ ] E5: install the release-please GitHub App before release automation (M7).
- [ ] Create environments `eval-live` (M2 recording) and `production` (MV).

## Criteria that stay unmet until the toggles are set

| Criterion | Depends on |
|---|---|
| D5 secret scanning and push protection on | Secret scanning toggles |
| D5 CodeQL on (M1-7 acceptance "CodeQL on") | CodeQL default setup |
| D5 full-SHA pinning enforced by policy | Actions pinning toggle (already true in every workflow, checked by zizmor) |
| D4 single required check `ci-gate` | M1-3 transition plus the required-check change |
| D5 immutable releases | Immutable releases toggle (needed by M7) |
