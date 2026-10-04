# Conservative dependency maintenance

## Scope and current activation status

Routine version updates target `develop`. No automatic merge into `main`, image
publication or deployment is part of this system. GitHub's native auto-merge is the
only merge mechanism; the controller never approves a review, directly merges,
rebases, pushes, or uses an administrative bypass.

Observed on 2026-09-27: this repository is **public**, the default branch is `main`,
and merge commits, squash and rebase merges are available. `develop` requires the
GitHub Actions `checks` context (app ID 15368), strict up-to-date checks,
conversation resolution and protection enforcement for administrators. Force pushes
and branch deletion are disabled. The approving-review count is currently zero;
this work does not change it. No additional rulesets were returned by the API.

The repository's `allow_auto_merge` setting has been enabled under the owner's
explicit authorization. **Unattended merging is not activated.** The policy fails
closed until all of these prerequisites exist:

1. The trusted workflow and policy scripts are available on the default branch.
2. `develop` requires both `checks` and **`Dependency policy`**, pinned to the GitHub
   Actions app, with strict freshness and administrator enforcement retained.
3. Repository variable `DEPENDABOT_AUTOMERGE_ENABLED` is exactly `true`.

Rechecked on 2026-10-04: policy workflow/scripts and Dependabot configuration
already exist on main `0d2511e6a9d2ab4a4da5c72c194c7a4eb8aa24b8`; those files match
the audited develop versions. The variable remains unset and `Dependency policy`
is not a required check. Default-branch file presence is therefore satisfied, while
actual privileged-token verification, required-check setup and authorized enablement
remain pending. Confirm check emission on ordinary PRs before requiring it, so
unrelated PRs are not stranded. No main merge is needed merely to install the
currently present files; future changes still require the normal authorized flow.
Do not promote an application release or weaken protections to activate automation.

Public repositories support these controls on GitHub Free. Private repositories
need the applicable paid plan for protection/auto-merge features; do not assume this
configuration transfers unchanged after a visibility or ownership change. Missing
or unreadable protection metadata prevents automation.

Live Actions runs `36336537107` and `36336760530` exposed a further activation gate:
the static job's read-only `GITHUB_TOKEN` cannot query the GraphQL protection data,
even with explicit pull-request read access. Its audit now records
`audit_state=permission_blocked`, `eligible=false`, `protections_ready=false` as
an observation, not a successful protection check. The merge controller still
throws/fails closed on that same error. Its separate write-scoped native-operation
token must be verified against the current trusted default-branch workflow, before enabling
the variable; its ability to read those fields is currently **unverified**.
Do not introduce a PAT or broaden organization permissions to conceal this gate.

## Eligibility

The allowlist lives in `scripts/dependabot_policy.py` and is intentionally small:

| Update | Automatic candidate | Reason |
| --- | --- | --- |
| `pytest` patch, same stable major/minor | Yes | Test runner exercised by both offline and real-service CI; minor/major runner behavior changes need review |
| `iniconfig` patch/minor, same stable major | Yes | Small test-configuration dependency; no runtime use; existing pytest verification remains mandatory |
| Compatible lockfile-only update | Only if every changed package follows the rows above | Full resolution compared, not just the named direct update |
| Other Python dependencies, including Ruff, mypy, FastAPI, providers, database and auth/security dependencies | No | Compiler/framework, runtime and persistence consequences require review; dev membership alone is insufficient |
| GitHub Actions/workflows, Docker/base images/OS | No | Privileged execution and platform changes require review |
| Major, prerelease, 0.x, post/local versions, downgrades, unknown versions, new/removed packages or changed dependency edges | No | Impact is not established by the narrow policy |

Every candidate must be an open, non-draft, same-repository Dependabot PR into
`develop`. Both the bot login and immutable GitHub account ID/type must match.
Every commit must identify that bot as author and have a verified GitHub web-flow
signature/committer identity; a human modification or ambiguous history goes manual.
Authenticated GitHub API commit/tree/blob data provides the dependency metadata.
PR titles, branch naming, labels and commit-message prose never authorize merging.

Only modified regular `uv.lock` and optionally `pyproject.toml` files are permitted.
Semantic comparison preserves all project scripts, tool settings, Python constraints,
runtime requirements, sources, markers and dependency edges. Only approved dev
version constraints and matching lock versions/artifacts may change. PyPI source,
artifact host/name and SHA-256 metadata are checked. Duplicate resolutions,
unaccounted transitive changes, symlinks, unexpected files or malformed metadata
require manual review. A group qualifies only when **every** change qualifies.
This is not a guarantee that a newly published package is free of malicious code.

## Native gates, reevaluation and privileges

`dependabot-policy.yml` runs on pull-request changes and completion of `Quality`.
It checks out **`github.workflow_sha`**, never the PR head or merge ref. It installs
no dependencies and executes only trusted policy code with hosted Python/gh.
PR files are parsed as TOML data fetched at immutable SHAs. No PR artifacts or
cache are downloaded into this privileged job. Its token is limited to contents,
pull requests and checks writes; no PAT, organization scope, production environment
or self-hosted runner is used. Every action is SHA-pinned.

For a Dependabot PR, the controller first places the current-head required policy
check on hold and revokes any previous native auto-merge setting. It then rechecks
identity, complete change scope, actual protection, successful required CI from the
expected app/current head, mergeability and ancestry against current `develop`.
New head/base/labels invalidate the snapshot. It arms native auto-merge while the
required policy check is still held, then releases that check. Native branch rules
still enforce approvals, conflicts, conversation resolution and strict freshness.
There is no bot review and no replacement for mandatory human approvals if those
are added later. A `workflow_run` success alone never authorizes a merge.

Unknown, failed, cancelled, pending, missing or duplicate required checks do not arm
auto-merge. Expected waits are reported as action-required policy results, with
reevaluation after Quality completes or after a new commit/rebase/reopen. API faults
leave a blocking hold and a redacted error. A maintainer can dispatch reevaluation
for the exact current SHA. Concurrency serializes decisions for the same head;
new-head events cannot reuse an old policy result. Required non-Check-Run status
providers are conservatively unsupported until reviewed.

GitHub token-generated events do not generally trigger additional workflows. This
repository relies on the already completed PR verification, not an assumed push
run after the bot merge. Publishing is a separate manual workflow, and there is no
production CD. Dependabot's own rebases generate new revisions requiring fresh CI;
the controller does not create commits or a custom rebase/event loop.

## Scheduling, security alerts and manual operation

Python updates run weekly with a seven-day version cooldown and at most three open
PRs; eligible test tools are separated from runtime review groups. Actions and
images retain a monthly schedule and two-PR bounds, with explicit automatic rebase
strategy. Security updates are not delayed by this routine version cooldown.

Dependabot security PRs target the **default branch**, even when routine version
updates target `develop`. They are therefore outside automatic eligibility and must
be reviewed promptly. Do not close/suppress alerts or pretend `target-branch`
redirects every security fix. A security label does not waive risk or CI checks.

Native rebasing is best effort, not indefinite: old PRs (notably after the documented
30-day window), conflicts and human modifications can require maintainer action.
Do not force-push human work or spam rebase comments. Review the affected PR and
request the supported Dependabot rebase/recreate operation only when appropriate.

- **Force manual review:** add `dependencies:manual` (an opt-out, never an approval),
  or use the workflow's `manual` dispatch with PR number and exact reviewed head SHA.
  Only a writer/maintainer/admin can take this path. It disables native auto-merge
  before passing the policy gate; all ordinary checks/reviews still apply. The manual
  decision is retained in the trusted current-head check metadata, including across
  retries and Quality completion, so a later event cannot re-arm that head. A new
  head requires fresh evaluation; use the label for a PR-wide opt-out. The dispatch
  is an explicit human decision, not authorization for future changes.
- **Pause:** set `DEPENDABOT_AUTOMERGE_ENABLED=false`, and disable native auto-merge
  on any already armed PRs immediately. A variable change alone does not trigger a
  run or retroactively cancel native intent. Dispatch reevaluation as needed; keep
  the workflow available to complete policy checks. Do not remove branch protection.
- **Recover:** revert a problematic update in a normal task PR to `develop`, run the
  full checks and review the resulting lockfile. Do not reset shared history or
  assume an application rollback reverses migrations.

## Verification and activation handoff

```sh
uv run pytest -q tests/test_dependabot_policy.py
bash scripts/check_workflows.sh
uv run python -m scripts.dependabot_automation --audit-pr <number>
```

The audit is read-only, including on closed PRs; it prints fixed decision reasons,
revision and protection readiness, never PR bodies or token values. CI runs the
same audit with its read-only contents/pull-request `GITHUB_TOKEN` and retains
`dependency-policy-audit.json` in static diagnostics. A specific permission denial
is reported as a blocking capability observation; unrelated API failures still fail
the audit command. The artifact cannot authorize merging. This tests actual API/token
visibility without enabling auto-merge. Unit tests cover eligible patches/minors,
whole manifests/lockfiles/groups, 0.x/prereleases/unknowns, spoofing, human commits,
file scope, native-gate ordering, stale heads, failed/missing CI and base/conflict
changes. They do not prove a live native merge or actual Dependabot rebase occurred.

After separate authorization for activation:

1. Verify the reviewed workflow/policy/configuration already on the default branch
   and identify any remaining version differences. Promote only necessary updates
   through a normal authorized protected PR. Keep automation paused.
2. Run the trusted policy on a current PR, verify its check is emitted by GitHub
   Actions, then add `Dependency policy` alongside existing required checks on
   `develop`; retain strict freshness, administrator enforcement and review rules.
3. Audit protections using the actual workflow token. Confirm the new check appears
   on ordinary PRs too before enabling the variable. Never add a required check
   whose trigger is unavailable or filtered away.
4. Enable the variable, inspect a genuine eligible Dependabot PR, verify its current
   head, Quality result, policy result and native auto-merge state. Confirm CI refresh
   when Dependabot rebases after `develop` advances. No fake vulnerability PR.
5. Record the genuine native merge/rebase run as separate live evidence. Until then,
   unattended native merging and rebase behavior remain **unverified**.

## Official references

- [Dependabot options and cooldown/rebase limits](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).
- [Security updates and target branches](https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/customizing-dependabot-prs).
- [Native auto-merge availability and controls](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-auto-merge-for-pull-requests-in-your-repository).
- [Privileged pull_request_target safety](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target).
- [Workflow event semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
