# CI and release preparation

## Active workflows

`Quality` runs on every PR into `develop`, manual dispatch, and trusted reusable
calls. There are **no path filters**: documentation/contract-only PRs still finish
the required gate. New commits cancel stale runs for the same PR/ref.

| Job | Purpose | Dependencies |
| --- | --- | --- |
| Static and offline | Frozen install, Ruff format/lint, strict mypy, pure tests, redacted history scan, deterministic contract drift | None |
| Real services and container | Real PostgreSQL/Neo4j migrations/indexing/integration tests; build image once, test non-root SSE/shutdown and actual Nginx routing | None |
| checks | Required aggregate; fails unless both jobs succeed, including cancelled/skipped failures | Both, with `always()` |

Tests are explicitly marked `integration`. Offline and real-service jobs run
disjoint selections, retaining all coverage. The container is built once with
BuildKit and reused for normal/shutdown/proxy checks. uv caches are keyed by the
lockfile with platform/Python-aware setup-uv behavior. BuildKit's content-addressed
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
has not been executed with a frontend release image.

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
