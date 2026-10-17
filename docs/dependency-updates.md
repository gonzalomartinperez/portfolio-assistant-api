# Manual dependency maintenance

The owner-selected profile is **manual merging for every update**. Dependabot opens
weekly routine proposals against `develop`; native `rebase-strategy: auto` refreshes
relevant young PRs and CI reruns for new revisions. Bounded PR limits, routine cooldown
and small groups reduce churn. About30-day-old, conflicted or human-modified PRs may
need manual intervention. No custom rebase bot or repeated comment loop exists.

Repository auto-merge is false; legacy activation flags are unset/false. The workflow
has only contents/read and pull-requests/read permissions, executes trusted base policy
code and never installs/runs PR code, approves, writes a check or arms/merges a PR.
The CLI rejects the old true activation flag. Retained controller fixture tests cover
historical safety cases; they do not activate that controller or prove live auto-merging.
No production credential, PAT or administrative bypass is used.

## Assessment and verification

Authenticated author/source/base/commits/files and complete manifests/lock resolution
are analyzed as untrusted data. Titles and labels never authorize anything. The narrow
low-risk cohort is described in `scripts/dependabot_policy.py`: a low-risk result
still requires human review and all current required Quality checks. Majors,
prereleases, unstable0.x, ambiguous metadata, unknown transitives, runtime/compiler/
framework, authentication, cryptography, persistence, Actions, OS/images, mixed-risk
groups, scripts and human-added commits require closer manual investigation.
`dependencies:manual` is a veto, not approval. No security alert is suppressed or closed
to force the routine-update policy.

Use `uv run python -m scripts.dependabot_automation --audit-pr <number>` locally,
or dispatch the trusted workflow with `gh workflow run dependabot-policy.yml -f number=<existing-pr>`.
This returns a head-bound risk report only. A workflow token that cannot inspect
protection reports permission_blocked without granting itself writer/admin permissions.
Missing protection visibility is not permission to weaken the actual protected branches.
Tests cover spoofing, grouping, file/script changes, human commits, wrong base, stale
heads, failed/missing checks, branch advancement and read-only behavior. Fixture results
are distinct from an actual GitHub run against an existing PR.

Required Quality `checks`, strict up-to-date checks, administrator enforcement and
normal reviews remain authoritative. The optional assessment job is not a required
check, so skipping human PRs cannot leave required contexts pending. It does not run
redundantly after every Quality execution. A failed/pending gate, conflict or blocking
review must be resolved before a normal merge; never use merge-anyway.

Security proposals use GitHub's default-branch behavior: `target-branch: develop`
does not redirect all security PRs from `main`. Keep alerts/proposals visible and
review them promptly through the appropriate protected workflow. Routine cooldown
never postpones security updates. Dependabot configuration and privileged event code
are activated from the default branch; a develop-only commit is not live evidence.

Pause routine proposals through a reviewed config PR; leave deferred PRs open with a
reason. Revoke any existing native request before claiming manual reconciliation.
Recover a bad merged dependency with a normal revert/fix PR and complete CI. An
application rollback does not reverse migrations or authorize infrastructure changes.
Skills and this file grant no standing merge, publication or deployment authority.

## Observed controls — 2026-10-17

An authenticated audit found zero open Dependabot PRs and no activation variables.
API `allow_auto_merge` was true from an older setup and was explicitly disabled and
re-read as false under the owner's manual decision. Main still requires strict
`checks` from GitHub Actions app15368 with administrator enforcement; no protection
was relaxed. Live assessment activation must be verified after default-branch promotion.

References: [Dependabot options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference),
[rebasing limitations](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/managing-pull-requests-for-dependency-updates),
[secure workflows](https://docs.github.com/en/actions/reference/security/secure-use).
