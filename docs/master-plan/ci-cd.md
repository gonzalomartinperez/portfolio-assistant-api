# CI/CD, containers, supply chain and release

Applies ecosystem sections 5 to 8. Research: [05](research/05-cicd-supply-chain.md), [11](research/11-containers-dynamic-ci.md), [10](research/10-standards-dependencies.md), [09](research/09-vps-ops.md). Baseline (audit.md): one workflow `quality.yml` with five jobs and an aggregate `checks`, SHA-pinned actions, no path filters, two cross-repo checkouts, Postgres built and migrated twice, Trivy by SHA-checked binary, `pull_request_target` dependency-policy workflow, three Dependabot ecosystem entries with limits 3, 2 and 2, no SBOM, provenance, CodeQL, zizmor, Scorecard, release automation or immutable releases, image 992 MB.

Nothing here publishes an image, changes repository settings or deploys: those are owner-only (ecosystem 15.4) and are listed as gated tasks in [roadmap.md](roadmap.md).

## 1. Workflow set

| File | Trigger | Content |
|---|---|---|
| `ci.yml` | `pull_request` to develop and main, `push` to develop and main, `merge_group`, `workflow_dispatch` | `classify` then the jobs of the selected profile, then `ci-gate`; calls reusable workflows from `engineering-standards` by SHA (`ci-python.yml`, `docker-build.yml`, `security.yml`) |
| `nightly.yml` | cron 03:00 ART | full mutation, flake detector, Schemathesis long run, stubbed-model SSE load and soak, ZAP API scan, osv-scanner, Scorecard, `scorecard.json` and ratchet check |
| `weekly.yml` | cron Monday after the dependency PR | link check of all docs, standards drift (`standards.lock`), CI duration report, `deps-weekly-guard` is the shared workflow |
| `eval-record.yml` | `workflow_dispatch` only, environment `eval-live` (no required reviewer; DR-04 hard stop in code) | incremental cassette re-record, embeddings snapshot, under the spend cap (PAA-D9) |
| `eval-live.yml` | `workflow_dispatch` only, same environment | golden pass^3 live, or full-set run; writes reports as private artifacts of 7 days, never raw answers to public logs |
| `agent-review.yml` | `pull_request` | Codex second-opinion review (connector or `openai/codex-action` with `drop-sudo`), Claude review on request; minimal permissions, max turns and budget, no secrets for fork PRs (ecosystem 15.6) |
| `release.yml` | push to `main` | tag from the release-please manifest, build once, SBOM, provenance, scan, publish to GHCR (disabled until MV, DR-13; the image stays a CI artifact), immutable GitHub Release with SBOM and attestation links |

Removed: `quality.yml` (split into the above), `dependency-policy.yml` (`pull_request_target`, retired by the owner rule, PAA-D14). Tracked scripts `ci_profile.py`, `ci_identity.py`, `check_workflows.sh`, `dependabot_automation.py`, `dependabot_policy.py` are deleted when their replacement lands (file-moves.md).

## 2. Dynamic graph and the `ci-gate`

```
classify (<= 30 s) ─┬─> static (ruff, import-linter, guard, vulture, mypy) ──┐
                    ├─> unit + property + architecture + evals-unit ─────────┤
                    ├─> integration (shards: PG18+pgvector, Neo4j 5.26) ─────┼─> build image ONCE ─> scan | container-tests | e2e+sse | load(nightly) ─> attest (release) ─> ci-gate
                    ├─> golden (cassette lane, profile assistant-quality) ───┤
                    ├─> contract (oasdiff, schemas, Schemathesis short, cross) ┤
                    └─> security (zizmor, gitleaks, CodeQL default setup, dependency-review) ┘
```

`ci-gate` (renamed from `checks`): `if: always()`, `needs` every job, passes only if each result is `success` or `skipped` and a skipped job is allowed by the active profile; a failed or cancelled job fails it. It is the only required check in the ruleset. `classify` is fail-closed: any diff error, unknown file or unknown event runs the `code` profile with everything on.

## 3. Profiles and the path map (draft `ci-profile.json`)

```json
{
  "version": 1,
  "default_profile": "code",
  "profiles": {
    "docs": {
      "match_only": ["**/*.md", "docs/**", "!docs/master-plan/ci-profile.json", ".github/ISSUE_TEMPLATE/**", ".github/pull_request_template.md"],
      "jobs": ["docs-checks", "secrets", "ci-gate"]
    },
    "harness": {
      "match_any": [".agents/**", ".claude/**", ".codex/**", "AGENTS.md", "CLAUDE.md", "scripts/validate_skills.py"],
      "jobs": ["skills-check", "agents-commands-test", "docs-checks", "secrets", "ci-gate"]
    },
    "workflow": {
      "match_any": [".github/**"],
      "jobs": ["actionlint", "zizmor", "pin-policy", "reusable-dry-run", "secrets", "ci-gate"]
    },
    "contract": {
      "match_any": ["contracts/**", "src/portfolio_assistant/presentation/**"],
      "jobs_extra": ["oasdiff", "schemathesis-short", "consumer-compile", "schema-examples"]
    },
    "assistant-quality": {
      "match_any": [
        "src/portfolio_assistant/ai/**",
        "src/portfolio_assistant/prompts/**",
        "src/portfolio_assistant/adapters/retrieval.py",
        "src/portfolio_assistant/adapters/providers/**",
        "src/portfolio_assistant/adapters/portfolio/**",
        "src/portfolio_assistant/domain/{evidence,graph,privacy,portfolio_paths}.py",
        "evals/**", "tests/evals/**", "migrations/**"
      ],
      "jobs_extra": ["golden-cassette", "retrieval-metrics", "attack-pack", "budgets"]
    },
    "code": {
      "match_any": ["src/**", "tests/**", "scripts/**", "scorecard/**", "pyproject.toml", "uv.lock", "justfile", "migrations/**", "infra/**", "deploy/**", ".python-version", "ci-profile.json"],
      "jobs": ["static", "unit", "property", "architecture", "integration", "build", "scan", "container-tests", "e2e-smoke", "mutation-incremental", "secrets", "security", "ci-gate"]
    },
    "deps-weekly": { "branch_prefix": "dependabot/", "jobs": ["all", "dependency-review", "license-check", "sbom-diff", "lockfile-lint", "image-rebuild-scan"] },
    "release": { "base_ref": "main", "head_ref": "develop", "jobs": ["all", "mutation-full-or-last-nightly", "golden-cassette", "image-sbom-provenance-verify", "changelog-check", "live-golden-check"] },
    "hotfix": { "head_prefix": "hotfix/", "label": "owner-authorized-hotfix", "jobs": ["code", "release-verification", "auto-back-merge"] }
  },
  "affected": {
    "integration": ["src/**/adapters/**", "src/**/application/**", "migrations/**", "infra/**", "evals/corpus/**", "tests/integration/**", "pyproject.toml", "uv.lock"],
    "image": ["src/**", "migrations/**", "contracts/**", "pyproject.toml", "uv.lock", "infra/docker/**", ".python-version"],
    "e2e": ["src/**/presentation/**", "src/**/bootstrap/**", "src/**/application/runs.py", "tests/e2e/**", "infra/docker/**"],
    "mutation": ["src/**/domain/**", "src/**/application/**", "src/**/ai/retrieval/**", "evals/harness/graders/**"]
  }
}
```

A unit test (`tests/harness/test_ci_profile.py`) asserts: every tracked file matches at least one profile; every job named in a profile exists in `ci.yml`; `docs` profile never matches a path under `src/` or `tests/`; a deliberately unclassified file (negative fixture) falls to `code`. `merge_group` is handled by the same classifier (merge queue is not adopted, E4).

## 4. Budgets and caching

| Budget (assistant API, ecosystem 6.2) | Target | Notes |
|---|---|---|
| PR critical path p50 / p95 | 5 min / 10 min (cassette lane, no network) | measured 2026-11-09 with `gh run list --workflow quality.yml --json startedAt,updatedAt`: six completed runs of 3.3 to 4.4 min, median 3.7 min (all were failing runs, so a floor for green runs); the weekly CI report keeps measuring it |
| Per job | classify 0.5 min, static 2, unit and property 3, integration 4 (shard if above), golden 2, build warm 3, scan 1.5, container tests 2, gate 0.1 | timeouts: 10 to 15 for unit and lint, 25 for e2e, 30 for image, 2 for the gate |
| Nightly | at most 60 min | live eval lane stays manual |
| Release | at most 45 min | |
| docs profile p50 | at most 2 min | |

Caching: uv cache keyed on `uv.lock` and `.python-version` (setup-uv), pytest and mypy caches keyed on lockfile plus source hash, Docker `buildx` cache `type=registry,mode=max` on `ghcr.io/gonzalomartinperez/portfolio-assistant-api:buildcache` (distinct from the worker target cache `...:buildcache-worker`), only default branches write broad caches. Postgres is no longer built twice: the database image comes from a digest-pinned upstream (`postgres:18.x-trixie`) plus the pgvector pg18 package decided once for both API repos; the corpus is indexed once per job from the frozen snapshot (PAA-D2), which also removes the two cross-repo checkouts of `portfolio` and `portfolio-backoffice`. The backoffice IAM compatibility fixture (today a pinned checkout plus `npm ci`) is replaced by a committed schema and fixture set exported from the contract (ecosystem invariant 1: no cross-repo imports), verified by the contract cross job.

## 5. Security hardening (zizmor-enforced)

| Control | Plan |
|---|---|
| Token | `permissions: {}` at workflow level; `contents: read` per job; `id-token`, `attestations`, `packages` write only on `release.yml` build and attest jobs |
| Actions | All `uses:` pinned to full SHA with version comment (already true); repository policy "require full-SHA pinning" on; reusable workflows from `engineering-standards` pinned by SHA |
| Checkout | `persist-credentials: false` everywhere except the release-please job |
| Triggers | No `pull_request_target`, no `workflow_run` with PR head checkout; untrusted context through `env:` only |
| Scanners | zizmor and actionlint on `.github/**` changes; gitleaks; secret scanning and push protection; CodeQL default setup (python, actions); dependency-review; osv-scanner daily; Scorecard weekly (fail if score drops by more than 1 point; accept the ceiling on Code-Review for a solo repo) |
| Egress | `step-security/harden-runner` audit then block with an allowlist on `release.yml` and eval jobs only (public repo; vendor product, [05] 3.15) |
| Environments | `production` environment with the owner as required reviewer; `eval-live` has NO required reviewer (controls: branch restriction, the code-level DR-04 hard stop and a separate provider key held only there); never available to fork PRs |
| Image scanner | Grype on the built digest, fail on fixable High or Critical (replaces the SHA-checked Trivy v0.75.0 binary; Trivy remains allowed as SHA-pinned binary at or after v0.35.0, E8) |

## 6. Supply chain for the image

SBOM CycloneDX via Syft attached as an attestation and as a release asset; provenance through `actions/attest-build-provenance` built in the isolated `attest-image.yml` reusable workflow, with `gh attestation verify oci://IMAGE@sha256:... --signer-workflow gonzalomartinperez/engineering-standards/.github/workflows/attest-image.yml` in the deploy path and in vps-ops before it records a digest. Claim only Build L2 now and L3 via the isolated workflow. Immutable releases are switched on (owner setting) before the first release; tag ruleset for `v*`. Install-time code: `uv sync --locked` with `exclude-newer = "7 days"` in `pyproject.toml`; lockfile diff reviewed in the weekly PR. Image publication is **not** deployment and needs owner approval (PAA-D15); until then PR and develop builds stay local to the runner and are scanned only.

## 7. Containers

### 7.1 Version matrix applied (ecosystem 8.1, data of 2026-11-09)

| Component | Today | Target |
|---|---|---|
| Python | `python:3.14.8-slim-trixie@sha256:a2b82f3c...` | `3.14.x-slim-trixie@sha256` (newest 3.14 patch via the weekly PR; `.python-version` stays in step); 3.15 as a non-blocking CI job; `requires-python >= 3.14,<3.15` stays until 3.15 is adopted |
| uv | 0.13.1 (read in the repo Dockerfile and `uv.lock` header at `e749ca7` on 2026-11-09; release source https://github.com/astral-sh/uv/releases; re-verify the newest release and digest at M1-4) pinned by digest in Dockerfile and `setup-uv` | same, bumped in the weekly PR; `UV_PYTHON_DOWNLOADS=0` (today `never`, equivalent) |
| PostgreSQL | custom `portfolio-assistant-postgres:18.6` image built from `infra/docker/postgres/Dockerfile` | `postgres:18.x-trixie@sha256` plus pgvector `pg18`, same choice as pequeverso-assistant-api; HNSW builds need `--shm-size` at least `maintenance_work_mem` |
| Neo4j | `5.26.32-community-trixie@sha256:f1e52d4d...` | `5.26.x-community` digest-pinned (standard names 5.26.33); decision PAA-D12 may remove it |
| Debian | 13 trixie | 13 trixie |
| Runner | `ubuntu-24.04` explicit | keep explicit label, never `ubuntu-latest` |

### 7.2 Canonical Dockerfile (target; digests resolved at M1, shown as placeholders)

```dockerfile
# syntax=docker/dockerfile:1@sha256:<pinned-frontend>
ARG PYTHON_IMAGE=python:3.14.8-slim-trixie@sha256:<resolved>
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.1@sha256:<resolved>

FROM ${PYTHON_IMAGE} AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/app/.venv/bin:$PATH

FROM base AS build
COPY --from=${UV_IMAGE} /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
COPY pyproject.toml uv.lock LICENSE THIRD_PARTY_NOTICES.md ./
RUN --mount=type=cache,id=portfolio-assistant-api-uv-py314,target=/root/.cache/uv,sharing=locked \
    uv sync --locked --no-dev --no-install-project --no-editable
COPY src ./src
RUN --mount=type=cache,id=portfolio-assistant-api-uv-py314,target=/root/.cache/uv,sharing=locked \
    uv sync --locked --no-dev --no-editable

FROM base AS api
ARG VERSION REVISION CREATED
LABEL org.opencontainers.image.title="portfolio-assistant-api" \
      org.opencontainers.image.source="https://github.com/gonzalomartinperez/portfolio-assistant-api" \
      org.opencontainers.image.version=$VERSION org.opencontainers.image.revision=$REVISION \
      org.opencontainers.image.created=$CREATED org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.description="Grounded portfolio assistant API" \
      org.opencontainers.image.documentation="https://github.com/gonzalomartinperez/portfolio-assistant-api/tree/main/docs"
RUN python -m pip uninstall --yes pip && rm -rf /usr/local/lib/python3.14/ensurepip
COPY --from=build --chown=65532:65532 /app/.venv /app/.venv
COPY migrations ./migrations
COPY contracts ./contracts
USER 65532:65532
STOPSIGNAL SIGTERM
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=8s --start-period=30s --retries=3 \
  CMD ["python","-c","import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=5)"]
CMD ["assistant-api"]   # console script; uvicorn --no-access-log --no-proxy-headers --timeout-graceful-shutdown 15

FROM api AS worker
USER 0
RUN apt-get update && apt-get install -y --no-install-recommends git=<pinned> && rm -rf /var/lib/apt/lists/*
USER 65532:65532
CMD ["assistant-knowledge-watch"]
```

Rules applied: no `latest`; digest pins for every `FROM`; `uv sync --locked`; cache id unique to this repo (P0-5, replaces `vps-ops-uv-python314`); no secrets in `ARG`/`ENV`; `SOURCE_DATE_EPOCH` from `git log -1 --pretty=%ct` passed by `docker-bake.hcl`; `.dockerignore` excludes `evals/`, `docs/`, `tests/`, `artifacts/`; amd64 only until the VPS architecture is known; stdlib `urllib` health check (no curl); `git` only in the `worker` target (the API needs none, and the 992 MB image carries it today); the API image drops to about the size of the dependency set. Size budget: **at most 500 MB, ratchet in `image.json`** (sibling is 368 MB). Hypothesis to measure in the first spike (half a day): the `lingua-language-detector` models dominate the layer size; if so, restrict the detector to the languages the product supports (EN, ES plus the unsupported-language policy needs) only if golden language items stay at 100%, otherwise accept a higher budget with the measurement recorded. Hardening at runtime (Coolify custom options or compose, ecosystem 8.3): `read_only`, `tmpfs /tmp`, `cap_drop: [ALL]`, `no-new-privileges`, `pids_limit`, `mem_limit` equal to `memswap_limit`, `stop_grace_period: 25s` (existing contract: at least 25 s).

Gates in CI: hadolint, dockle, container-structure-test (user, labels, entry points, no `git` in `api`), Grype, then attest. `docker-bake.hcl` is the single entry point locally and in CI.

Health contract: `GET /healthz` (liveness, `{status, version}`) and `GET /readyz` (readiness with `version` and `schema_version`, 200 or 503) are added next to the existing `/health/live` and `/health/ready` (expand), the Dockerfile and docs move to the new names, the old names are removed in the next minor after vps-ops confirms (contract phase, `contract-major` not needed because health is operational, ADR recorded). Entry points: console scripts `assistant-api`, `assistant-migrate`, `assistant-retention`, `assistant-knowledge-sync`, `assistant-knowledge-watch`; `python -m app.migrate` and friends in `docs/deployment-contract.md` and vps-ops compose change together through a `releases/production.lock` PR (ecosystem 18.1, cross-repo dependency on vps-ops, tracked in roadmap M4).

## 8. Dependabot: weekly single PR (ecosystem 5)

```yaml
version: 2
multi-ecosystem-groups:
  weekly:
    schedule: { interval: weekly, day: monday, time: "09:00", timezone: America/Argentina/Buenos_Aires }
    target-branch: develop
updates:
  - package-ecosystem: uv
    directory: /
    multi-ecosystem-group: weekly
    patterns: ["*"]
    open-pull-requests-limit: 1
    cooldown: { default-days: 7, semver-major-days: 14, semver-patch-days: 3 }
  - package-ecosystem: github-actions
    directory: /
    multi-ecosystem-group: weekly
    patterns: ["*"]
    open-pull-requests-limit: 1
  - package-ecosystem: docker
    directories: ["/infra/docker/api", "/infra/docker/postgres"]
    multi-ecosystem-group: weekly
    patterns: ["*"]
    open-pull-requests-limit: 1
```

Security-update PRs are switched off in repository settings (alerts stay on); the daily `osv-scanner` job notifies and a critical reachable vulnerability follows the manual path of ecosystem 5.5. The shared `deps-weekly-guard` closes duplicates, keeps the survivor current with `develop` and labels red PRs `needs-fix`. The four unverified behaviours (ecosystem 5.4) are proven once on a sandbox repo by `engineering-standards` before this file is merged; until then the existing `dependabot.yml` stays untouched; if behaviour (1) fails in the sandbox, the guard's supersede flow (close the older PR, keep one) replaces in-place updates and the result is recorded in an ADR. The weekly PR carries the `deps-weekly` profile: full pipeline plus dependency-review, license check, SBOM diff, lockfile lint and image rebuild with scan. Pins to watch because they ride the same PR: Python patch, uv, `neo4j` driver, `openai`, `langgraph*`, `langchain-core`, `langsmith` (pinned exactly today), `lingua-language-detector` (pinned exactly, large), Neo4j and Postgres image digests (digests older than 30 days fail the guard).

## 9. Release automation

release-please (manifest mode) on `develop` keeps one release PR with the version bump in `pyproject.toml` and `CHANGELOG.md` (Keep a Changelog sections); on promotion to `main` the workflow tags `vX.Y.Z` and creates an immutable GitHub Release with SBOM and attestation links. Needs a GitHub App token (E5, owner grants scope). First planned version: **1.1.0** at M7 (additive contract v1.1, internals changed, wire v1 preserved); `main` untouched until then. Images carry `vX.Y.Z` and `sha-<short>` tags for humans; deploy by `@sha256` digest only. Post-release verification (Phase V): `/readyz` version equals the release SHA.

## 10. Rulesets (applied by the standards script, owner runs it)

`develop` and `main`: PR required, `ci-gate` required and strict, no force push or deletion, no bypass actors (never `--admin`), tag ruleset for `v*`. Today: strict `checks` and enforced administrators are on, zero required approvals, no rulesets (2026-10 audit A4). Migration changes the required check name from `checks` to `ci-gate` in one step with both names required during the transition PR.
