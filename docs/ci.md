> Current privacy boundary (2026-10-13): CI no longer uploads image archives or diagnostic
> artifacts from this public repository. The unsafe legacy candidate publisher was removed, along with its
> package-write permission. A private accepted publishing path is a separate release gate.
> Historical artifact instructions below do not authorize reactivation.

# CI and release preparation

## Active workflows

`Quality` runs on every PR into `develop` or `main`, manual dispatch, and trusted reusable
calls. There are **no path filters**: documentation/contract-only PRs still finish
the required gate. New commits cancel stale runs for the same PR/ref. Hosted jobs
use the explicit Ubuntu24.04 LTS label, matching the paired backoffice profile;
the moving ubuntu-latest alias is rejected so an announced runner-major migration
cannot silently change the validated environment. Runner patch images remain
GitHub-managed and are recorded by Actions.

| Job ID / human name | Purpose | Needs |
| --- | --- | --- |
| workflows / Workflow validation | Pinned actionlint and trusted-event syntax; no dependency install or secret token | None |
| secrets / Secret scan | Redacted full reachable history/worktree patterns; no public raw logs | None |
| static / Static checks | Frozen install, license/skills, Ruff, strict inner typing, bilingual bank, offline/contract/architecture negatives and deterministic drift | None |
| database / Database tests | Real PostgreSQL/Neo4j migrations/indexing/integration, bilingual fixture evaluation and scoped two-app IAM/recovery | static |
| container / Container verification | Own isolated databases/corpus, explicit recipe build, full scans, non-root streaming/SIGTERM/proxy and tested image identity | static |
| checks / Required checks | Always-evaluated fail-closed aggregate over every five prerequisites | All five |

The exact paired profile is enforced by scripts/ci_profile.py and its negative
fixtures. PRs and pushes to develop/main, merge-group, manual and reusable events
retain verification; no path filter can omit a required job. Main/develop post-merge
runs prove their actual merge commits, independently of prior PR merge-ref checks.

Static checks compile the authored bilingual question bank and reject generated
drift. The real-service job exercises ten development cases spanning all topics and
both locale hints through the HTTP/SSE harness; failed terminals fail the job.
Full 1000-case fixture runs are recorded locally rather than adding that cost to
every PR. These checks establish executable coverage, not live-model answer quality.

Tests are explicitly marked `integration`. Static and database jobs run
disjoint selections, retaining all coverage. Container smoke owns fresh services;
a completed database job cannot leave a fixture on another runner. The container is built once with
BuildKit and reused for normal/shutdown/proxy checks. uv caches are keyed by the
lockfile and `.python-version`, with platform-aware setup-uv behavior. uv itself
is pinned to 0.13.1, matching the production image. Only the static job saves this
shared dependency cache; runtime jobs restore it and installs the same frozen lock
without a competing upload. A cache miss still performs the complete install. BuildKit's content-addressed
cache includes the Dockerfile, frozen lock and source layers; its GHA scope is
`api-linux-amd64`. Cache entries never replace checks. Only the bounded synthetic project-database receipt is uploaded for seven days.
Other test diagnostics remain in Actions logs; no public image archive is uploaded.

Both service jobs build/load the PostgreSQL fixture with the same explicit
`linux/amd64` recipe and `postgres-linux-amd64` GHA v2 cache scope. BuildKit content
keys include the recipe, pinned base and copied inputs; changing a source SHA does
not discard unchanged layers. Each isolated runner still needs its own loaded
image. Compose uses `--no-build --pull never` to consume that verified image.
Only the container job exports this cache, and only on pushes to protected
`develop`/`main`; PRs, merge groups and dispatches restore without writing it.
A cold/evicted cache still runs the full build. No cache hit skips migrations,
service tests, scans or shutdown checks. Negative profile fixtures reject a
second/untrusted writer, wrong platform/scope, skipped load and implicit rebuild.

Both builders pin Buildx v0.38.0 and the BuildKit image digest
`sha256:cec9f139f45e93c5c69c60f8b07cfad9f43f4ef6b6a6cd917527fea5ff2e3dea`.
These tool pins are separate from action SHA pins. Cache isolation follows
[GitHub ref restrictions documented by Docker](https://docs.docker.com/build/cache/backends/gha/);
[setup-buildx](https://github.com/docker/setup-buildx-action) documents the version
and driver options. No credentials, provider calls or registry publication are
added. Actual cold/warm Actions observations belong in release evidence; a cache
configuration alone is not a measured speedup.

Third-party actions are pinned to reviewed upstream commit SHAs. PR jobs have only
`contents: read`, do not persist checkout credentials, receive no deployment/model
secrets and never use `pull_request_target`. Fixture credentials belong solely to
ephemeral CI databases. No active workflow grants registry write permission. The earlier candidate
publisher and public image-archive uploads were retired for privacy. Local release
manifest validation remains; an authorized private publication path and registry
visibility decision are separate release gates. A merge cannot publish or deploy.

## Deployment belongs to vps-ops

Coolify, coordinated by the private vps-ops repository, is the only selected
production deployment platform. Application workflows validate/build images and
prepare authorized immutable publication. Publication is not deployment approval.
Package visibility must be confirmed independently from repository visibility.
No publication has been authorized for this phase.

The old deployment template, apply-release script and production Compose/TLS
configuration were retired after explicit vps-ops ownership acceptance. They remain
in Git history. Local proxy configuration moved to tests/fixtures/proxy and cannot
serve as production configuration. vps-ops owns approvals, serialization, routing,
migration scheduling, verification and rollback; see the
[Docker ownership handoff](docker-layout-handoff.md).

## Observed Actions duration

Before splitting jobs, required Quality checks took 60 seconds for PR #7,
80 seconds for PR #8 and 107 seconds for PR #9 (including added image/shutdown
smoke). The first parallel run (#10, run 36320177528) passed with static/offline 25 seconds,
real services/container 109 seconds and aggregate 3 seconds; diagnostic artifacts
were verified via the Actions API. These runs have different test scope/cache state;
they are not a controlled claim of a fixed percentage speedup.

## Main promotion gate

Promote through a `develop` → `main` PR after explicit owner authorization. Wait
for all five prerequisite jobs and the `Required checks` aggregate on that PR’s current head; do not
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

Both `develop` and `main` now require the aggregate `checks` with strict base
freshness. Main previously had PR protection but no required status check; this
gap was closed without changing its review count, administrator enforcement,
conversation-resolution or force-push/deletion restrictions. Merges cannot rely
only on an operator remembering to wait for CI.

## Conservative dependency automation

See [dependency maintenance](dependency-updates.md) for the allowlist, manual path,
activation prerequisites and protection evidence. The existing static job now runs
a read-only GitHub API audit on PRs and retains `dependency-policy-audit.json`; it
has only contents/pull-request read permissions and does not authorize merging.
A denied protection query is recorded as `permission_blocked` with eligibility
and protection readiness false; the privileged controller still fails closed on
unreadable controls. This diagnostic is not the required authorization gate. Offline policy tests run
in the existing test suite, without duplicating builds or integration tests.

`dependency-policy.yml` is a separate trusted-metadata controller. Its single job
checks out the trusted workflow SHA, installs no PR dependencies, uses no PR cache
or artifact, and can only manage a required policy check and native auto-merge.
It does not run the test suite. Completion of Quality triggers revalidation of the
actual PR/current head, not unconditional merging. Per-head concurrency serializes
competing decisions; new heads need a new required policy result. No path filter
can omit the policy on an ordinary PR after activation. Manual/unverifiable updates
receive an explicit action-required result, not a permanently pending hidden job.
API failures leave a blocking hold, recoverable through explicit reevaluation.

As of the 2026-10-04 audit, trusted policy files already exist on main. Required
policy-check configuration, privileged-token verification and authorized variable
enablement remain pending; file presence alone does not activate automation.
Confirm ordinary-PR check emission before making it required. See the dated state
in dependency-updates.md. Production workflows remain absent/disabled.

## Python 3.14 application compatibility

Frozen installs select Python 3.14.8 from `.python-version` with uv 0.13.0; the
image uses the same pinned Python patch on Debian slim. Privileged dependency/release scripts intentionally
remain Python 3.12-compatible because those trusted jobs use the hosted runner
system interpreter without installing PR dependencies. Ruff per-file targets and
a grammar test enforce this distinction. They do not fall back for application checks.


Current container increment: PR #37, source
`badf49dd931660fe674073abc70d3a8c696a37f5`, passed
[Quality run 38021519477](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/38021519477).
Static/offline took 31 s; real services/container 179 s; aggregate 3 s. Integration
included the updated runtime build, tool-exclusion checks and shutdown/proxy smoke.
These jobs still run in parallel and retain disjoint suites. The cold security-package
layer differs from the prior build, so these times are not a controlled speedup claim.


## Image security policy

The existing integration job scans the image it already built; there is no second
build or privileged scan of PR code. Trivy 0.75.0 is fetched from its upstream
release and verified with a reviewed archive SHA-256 before execution. It produces
a complete OS/language report without ignore files or severity filtering. The
maintained `scripts.image_security` gate validates schema, OS inventory and the
actual Docker image ID; malformed, missing or stale reports fail closed. All
CRITICAL findings and HIGH findings with an available fixed version fail Quality.
Unfixed HIGH findings remain counted and visible in the retained full artifact;
they require assessment before production and are not approved by a green gate.
This is an added remediation gate, not a clean-image or production-security claim.
Scanner network failures fail the job. No production secrets or publishing token
are available to the job. The required aggregate `checks` remains unchanged.

Local policy tests: `uv run pytest -q tests/test_image_security.py`. Full report
and summary are retained with integration diagnostics even on failure. Scan the
release digest again at release selection: the vulnerability database changes
independently of source/image revisions.


The integration job now builds infra/docker/postgres/Dockerfile once and uses the tested
non-root image for its owned Compose fixture. It supplies that exact container ID
to the existing two-service evaluation guard and stops only its fixture even on
failure. PostgreSQL logs are captured before artifact upload. The complete database
scan and matching-image summary are ephemeral; raw inventories are not uploaded.
The supported-base candidate tightens the PostgreSQL gate to reject every CRITICAL
and fixable HIGH finding through the same validated CLI as the application image.
Unfixed HIGH findings still require explicit production assessment. The API's
all-CRITICAL gate is unchanged. Full Neo4j Java scanning is
recorded separately for release assessment because its advisory database is ~936 MiB;
it is not represented as a green per-PR security gate. No extra API build or paid
provider call was added. Actual current-head Actions remains the merge gate.


## Executed overnight verification

Actual current-head Quality runs on 2026-10-10, before protected develop merges:

| Increment | Run | Static/offline | Real services/container | Aggregate |
| --- | --- | --- | --- | --- |
| Runtime security, PR #40 | [38024426083](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/38024426083) | 27 s | 133 s | 3 s |
| PostgreSQL image, PR #41 | [38025993266](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/38025993266) | 36 s | 219 s | 3 s |
| Reviewed artifact action, PR #31 | [38026495119](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/38026495119) | 30 s | 148 s | 3 s |

All jobs passed. These are hosted-runner observations, not controlled performance
comparisons. PR #41 adds the necessary PostgreSQL build and complete scan; no test
coverage was removed for speed. Its downloaded diagnostics confirmed 25 integration
tests with zero failures/errors and full image reports. Local combined verification
passed 291 tests. PR #31 changed four SHA-pinned upload-artifact references to 7.0.2;
the successful run exercised the updated action. This major update received manual
review, not blanket Dependabot auto-merge permission. Native protection remained
strict and the current head was matched at merge. Main and publication/deployment
workflows were not activated.

## PostgreSQL 18 current-head verification

PR #46 passed Actions `38289478519`: static/offline 35 seconds, real-service/container
168 seconds, aggregate gate 2 seconds. The previous run failed because the scanner
referenced the old local image tag; the selected 18.6 image is now scanned explicitly.
No scanner gate or required check was relaxed. The observability suite adds an actual
loopback OTLP receiver to the existing offline job and SQL persistence to the existing
real-service job; no new production job/controller is introduced.

## Private operations final code gate

PR #47 passed current code head `017df0c3036a3a976cf3b016b783f2932be31d7d` in
Actions `38293707505`: static/offline 30 seconds, real-services/container 186 seconds,
aggregate `checks` 4 seconds. Both independent jobs ran in parallel. Earlier heads
were cancelled by the existing concurrency rule after follow-up fixes; their green
checks were not used for the merge. No coverage, scanner or protection was weakened.
See the dated private-observability report for exact local/CI artifact limits.

Dependabot PR #48 replaced conflicted #44 through native maintenance, included
14 reviewed updates and passed Actions `38295075616` at exact head
`95c94291453ce6152de21a6b9748c410f367f3c9` (35/239/3 seconds). Framework/provider/driver
updates received manual review. Protections still require strict up-to-date `checks`
with administrators enforced; no blocking review or gate was bypassed. No open
Dependabot PR remained after that merge. New scheduled PRs need fresh evaluation.

## Vendor database release assessment

An explicit manual Quality dispatch with `verify_vendor_image=true` additionally scans the exact pinned Neo4j OS
and Java inventory without adding a second build or server lifecycle. Normal PR
coverage is unchanged; it does not claim this expensive Java release assessment ran.
See [receipt and unresolved release gates](verification/neo4j-vendor-refresh-2026-10-17.md).
Implicit Docker build-record artifact upload is disabled; build logs/summaries remain.

The default false input runs ordinary complete source/runtime validation; it is not
an accepted database assessment. Selected-digest OS/Java assessment and every unresolved
critical finding remain mandatory **external release-selection gates** for vps-ops.
No publication/deployment controller is activated here. The rejected candidate run and
known baseline findings remain recorded; no source tag waives them.

The optional `workflow_call` inputs retain their historical `frontend_commit` /
`frontend_image` names for caller compatibility. The selected source is now canonical
`portfolio-backoffice`, and pairing compares the actual private operations, product
and feedback schema bytes. Its archived public chat/SSE snapshot is not a current
chat consumer and cannot establish native portfolio compatibility. Current native
browser/API verification belongs to the portfolio. This opt-in source comparison is
not live OAuth/HTTPS pairing or a release-controller/deployment authorization.

The real-services job also reads an exact committed backoffice revision, installs
its frozen dependencies with a lock-keyed Node cache, and exercises both applications'
actual migrations/authentication against a fresh restricted project engine. The
owned fixture runner verifies independent recovery, restart and fresh-cluster
restore; it never uses the job's corpus fixture for destructive recovery. Only its
synthetic aggregate receipt is retained, not IAM logs, credentials or archives.
The required `checks` gate still requires both existing jobs. This adds application
compatibility coverage without a second API image build or privileged PR execution.


## Paired profile source and artifact privacy

The locally encoded profile follows the owner-coordinated contract revision
`eb8288349f797d1fd5d51bfc349e70da8eaf3c01`; public CI neither checks out nor depends
on that private repository. Commands above are this application's adapters to the
common job identities. No empty/dummy job replaces real verification.

Database/container jobs build only their own required fixtures. The API application
image is built once in container and reused for scan/stream/shutdown/proxy tests.
No cross-job image archive is uploaded. A same-SHA/config fixture rebuild is an
explicit privacy tradeoff; caches accelerate it without becoming provenance.
ci_identity records actual checkout/base/workflow SHA, run/attempt, platform,
reviewed input hashes and inspected local image IDs. Dirty/unverifiable build
inputs fail before identity is reported. IDs are not published registry digests.
Only redacted synthetic database receipts may be uploaded; no env files, session
artifacts, prompts/answers, backups or raw telemetry are included.

The required context changes from checks to Required checks. First obtain the
new actual GitHub Actions context in green, add it alongside the old requirement,
verify both remain required and then remove only the obsolete context. Preserve
strict freshness, producing app identity, admin enforcement and all other rules.
Never disable protection, add a green legacy placeholder or bypass a pending gate.
Actual protection and post-merge execution evidence must be recorded after this
transition; YAML/test success alone does not establish remote enforcement.

Official references checked:
[GitHub required-check semantics](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks),
[job dependencies](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-jobs)
and [source/workflow environment identity](https://docs.github.com/en/actions/reference/workflows-and-actions/variables).
