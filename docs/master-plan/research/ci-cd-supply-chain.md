# Research: CI/CD and supply chain

Planning research only. Workflow, repository-setting and publication changes each need
their own authorized task; image publication is not deployment approval (AGENTS.md).

## Target job graph (`quality.yml`)

```text
workflows ─┐
secrets ───┤
lint ──────┤  (ruff, format, mypy strict, skills, license, bank --check)
unit ──────┤  (pytest -n auto, coverage, junit, Hypothesis ci profile)
           ├─► build-image (app + postgres, once; GHA cache; outputs digest; SBOM)
           │      ├─► integration (services + migrate + index; combined coverage)
           │      ├─► container (smoke, proxy, Trivy over the already-built digest)
           │      └─► contract (schemathesis against the image; oasdiff vs base)
codeql ────┤  (default setup or own workflow)
dep-review ┘  (PR)
           └─► checks (aggregate, required)
nightly: mutation, property 2000, load smoke 2 min, deep vendor scan, Scorecard
```

- **Dedupe:** a composite action `.github/actions/prepare-stores` (Neo4j service, pinned
  checkout, build/load Postgres from cache, migrate, index) used by `integration` and
  `container`; or a single `integration+container` job if the parallelism does not pay
  off.
- **Build once:** the image is built in `build-image` and passed through a `docker save`
  artifact or a local cache registry; downstream jobs do not rebuild.
- **uv:** `setup-uv` with `enable-cache`, `cache-dependency-glob: uv.lock`, `save-cache`
  only on `develop`/`main` (already partially), `uv sync --frozen --no-install-project`
  in lint; `UV_PYTHON_DOWNLOADS=never` + a fixed `python-version`.
- **Parallelism:** `pytest -n auto` (xdist) in unit; integration partitioned by
  directory if it exceeds 2 min.
- **Reporting:** `junit` → job summary (for example `dorny/test-reporter` or an own
  `$GITHUB_STEP_SUMMARY`), coverage in the summary; flakes: `pytest --reruns` is
  **forbidden** in the gate; flakes are recorded in nightly with 3 repetitions to detect
  them.

## Duration budget

| Job | Today | p95 target |
|---|---|---|
| lint + unit (parallel) | 32 s (together) | ≤ 45 s each |
| build-image | inside container | ≤ 60 s with cache |
| integration | 206 s | ≤ 150 s |
| container | 143 s | ≤ 90 s (no rebuild) |
| contract | — | ≤ 60 s |
| **PR wall time** | 3.3–4.2 min | **≤ 4 min** with more coverage |
| nightly | — | ≤ 45 min |

## Supply chain and vulnerability policy

- **P0 (no code):** enable secret scanning + push protection (free on public
  repositories), CodeQL default setup for Python and Actions,
  `actions/dependency-review-action` on PRs, OpenSSF Scorecard (README badge: a strong
  signal for technical recruiters).
- **SBOM and provenance:** generate a CycloneDX/SPDX SBOM of the image (Syft or Trivy)
  and attest with `actions/attest-build-provenance` + `actions/attest-sbom`; verify with
  `gh attestation verify`. Aims at SLSA Build L2/L3 [source: SLSA v1.1]. Publish to
  GHCR only with explicit approval (AGENTS.md: publication ≠ deployment); vps-ops already
  selects by digest.
- **Python dependency scanning:** `osv-scanner` or `pip-audit` over `uv.lock` on PRs (in
  addition to the image Trivy scan).
- **Tiered policy (ADR-018):**
  - App image and own Postgres: **block** CRITICAL and HIGH with a fix (already exists).
  - Vendor (Neo4j): does not block PRs; weekly deep scan; automatic issue; **OpenVEX**
    statements for non-applicable findings (for example `linux-libc-dev` = kernel
    headers, not the running kernel ⇒ `not_affected / vulnerable_code_not_present`,
    with justification); SLA: CRITICAL with a fix ≤ 7 days, HIGH with a fix ≤ 30 days;
    no fix: monthly review.
  - The 4 Jackson HIGH findings (shaded copies in `parquet-jackson-1.18.1.jar`) are
    resolved by the ADR-017 decision (verified CalVer upgrade or removal of Neo4j).
- Replace or complement `scripts/scan_secrets.py` with a pinned `gitleaks` (MIT): less
  in-house code to maintain, community rules.

## Release and promotion

- Conventional Commits (already in use) → **release-please** generates CHANGELOG + tag +
  GitHub Release on `main`; enable GitHub **immutable releases**; the image of the
  release commit carries the attestation and SBOM as assets.
- Flow: task branch → PR to `develop` (checks) → PR `develop → main` (checks + dispatch
  of the capability sample if `app/ai/**` changed) → release → vps-ops chooses the digest
  (outside this repository).
- Required checks: `Required checks` (aggregate) + `CodeQL` + `dependency-review`. Keep
  0 reviews (single maintainer) but enable CODEOWNERS to document ownership.
- Review the volume of governance scripts (`dependabot_automation.py` 396 LOC,
  `dependabot_policy.py` 255 LOC, `ci_identity.py`, `release_manifest.py`…): each must
  justify its cost against a standard action; target −30% LOC in `scripts/`.
