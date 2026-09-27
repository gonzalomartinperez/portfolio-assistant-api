# CI and release preparation

## Active workflows

`Quality` runs on every PR into `develop` or `main`, manual dispatch, and trusted reusable
calls. There are **no path filters**: documentation/contract-only PRs still finish
the required gate. New commits cancel stale runs for the same PR/ref.

| Job | Purpose | Dependencies |
| --- | --- | --- |
| Static and offline | Pinned actionlint, frozen install, Ruff format/lint, strict mypy, pure tests, redacted history scan, deterministic contract drift | None |
| Real services and container | Real PostgreSQL/Neo4j migrations/indexing/integration tests; build image once, test non-root SSE/shutdown and actual Nginx routing | None |
| checks | Required aggregate; fails unless both jobs succeed, including cancelled/skipped failures | Both, with `always()` |

Tests are explicitly marked `integration`. Offline and real-service jobs run
disjoint selections, retaining all coverage. The container is built once with
BuildKit and reused for normal/shutdown/proxy checks. uv caches are keyed by the
lockfile and `.python-version`, with platform-aware setup-uv behavior. uv itself
is pinned to 0.9.13, matching the production image. Only the static job saves this
shared dependency cache; integration restores it and installs the same frozen lock
without a competing upload. A cache miss still performs the complete install. BuildKit's content-addressed
cache includes the Dockerfile, frozen lock and source layers; its GHA scope is
`api-linux-amd64`. Cache entries never replace checks. Failure/success diagnostic
artifacts retain JUnit and redacted JSON summaries for seven days. A tested image
archive is exported only for trusted manual publishing, not every PR.

Third-party actions are pinned to reviewed upstream commit SHAs. PR jobs have only
`contents: read`, do not persist checkout credentials, receive no deployment/model
secrets and never use `pull_request_target`. Fixture credentials belong solely to
ephemeral CI databases. Registry write permission exists only in the manual
publisher's final job. User inputs enter shell steps through environment variables
and are validated as full hashes/digests before use.

`Publish tested candidate (manual)` accepts an immutable frontend image and its
owner's committed revision. It reuses Quality, including cross-service proxy smoke and exact committed frontend contract-byte comparison,
then publishes the **tested image archive** without rebuilding it. The artifact
`release-candidate-manifest` records both image digests, both commits and contract
version, with `production_authorized: false`. Manual publishing is prepared but
has not been executed with a frontend release image. GitHub discovers dispatchable
workflows on the default branch, `main`. The owner has authorized promoting the
fixture-backed candidate from `develop` after successful CI. Once merged, manual
publishing becomes discoverable; merging alone neither publishes images nor deploys.

## Deployment remains disabled

`.github/workflow-templates/deploy-vps.yml` is deliberately outside the active
workflow directory. It describes serialized deployment behind a `production`
environment. Before activation, the owner must authorize the combined release,
configure required human reviewers, approve a restricted SSH transport and known
hosts, and verify backup/migration compatibility. No current workflow deploys
`develop`, accesses the VPS, changes DNS, or merges `main`.

`deploy/apply-release.sh` is an operator-only entry point for an approved VPS.
It validates paired immutable images, applies reviewed forward migrations, starts
those digests and verifies readiness plus real no-evidence SSE through HTTPS.
Rollback means applying the previous **schema-compatible** manifest. Database
restore/recovery is a separate reviewed procedure; rolling back an image never
undoes a migration.

## Observed Actions duration

Before splitting jobs, required Quality checks took 60 seconds for PR #7,
80 seconds for PR #8 and 107 seconds for PR #9 (including added image/shutdown
smoke). The first parallel run (#10, run 36320177528) passed with static/offline 25 seconds,
real services/container 109 seconds and aggregate 3 seconds; diagnostic artifacts
were verified via the Actions API. These runs have different test scope/cache state;
they are not a controlled claim of a fixed percentage speedup.

## Main promotion gate

Promote through a `develop` → `main` PR after explicit owner authorization. Wait
for both Quality jobs and the aggregate `checks` on that PR’s current head; do not
reuse a check from an earlier head or bypass reviews. The same workflow runs without
path filters on both target branches. This promotes the verified fixture candidate;
production/live-model limitations in the release checklist remain in force.

## Dependency maintenance and job audit

The two independent verification jobs deliberately remain parallel. Splitting lint,
formatting and typing into separate runners would repeat checkout/install overhead;
the expensive real-service/image work already overlaps all offline checks. We keep
one image build and disjoint test selections. No path filters, skipped required
checks, reduced test coverage or automatic major-version merge is introduced.
Every operative check has a descriptive step name. The aggregate gate and manual
publisher input-validation job have no GitHub token permissions; the latter no
longer checks out source just to validate two strings. Deployment remains disabled.

`scripts/check_workflows.sh` validates active workflows and the disabled deployment
template in CI using actionlint 1.7.12 with a reviewed archive SHA-256. Updating
that tool requires reviewing both version and checksum. Third-party action updates
remain immutable SHA references, checked against the upstream release tag. Checkout
7.0.1 and Buildx setup 4.4.1 use Node 24 on compatible GitHub-hosted runners; no unsafe
fork-checkout override or persisted credentials are enabled.

Dependabot groups routine minor/patch version updates by ecosystem to reduce
repeated PR pipelines. Major updates remain individual reviewable PRs; grouping
never grants automatic merge. Python minor/major image changes are excluded from
routine updates because changing Python requires an explicit project decision.
Security alerts and default-branch security PRs must still be reviewed separately
from the scheduled version updates targeting develop. Before merging any update,
review its diff/upstream notes, run the full gate on the current head and honor
strict base freshness. Promotion to main receives its own complete check.

Sources: [Dependabot options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference),
[checkout release](https://github.com/actions/checkout/releases/tag/v7.0.1),
[Buildx setup release](https://github.com/docker/setup-buildx-action/releases/tag/v4.4.1).

Repository security settings were verified on 2026-09-27: Dependabot vulnerability
alerts and automatic **creation** of security-fix PRs are enabled. Automatic merging
is not enabled by this configuration. Initial alert queries returned no open alerts;
that is not a guarantee that future scans will find none. Security fixes targeting
the default branch also run the full Quality gate.
