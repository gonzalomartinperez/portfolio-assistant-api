# ADR017: Canonical API image with `api` and `worker` targets

Status: accepted (2026-11-14, master plan task M1-4 part a).

## Context and problem

The application Dockerfile built one image that carried Git for the public-source
corpus CLI, installed only the dependencies (`--no-install-project`), so no console
script existed, and reused a BuildKit cache id copied from vps-ops
(`vps-ops-uv-python314`, audit P0-5). The API process needs no Git. The
[image size spike](../evidence/image-size-spike-2026-11-14.md) measured 662.5 MB:
`lingua` is 306 MB, the apt layer with Git 104 MB.

## Decision

1. One Dockerfile, stages `base`, `build`, `worker`, `api`. `api` is last so the
   existing CI build without `target:` keeps building it. `base` holds the pinned
   security packages and removes pip; Git and its pinned dependencies are installed
   only in `worker`.
2. The project is installed editable (`uv sync --locked --no-dev`) after the
   dependency layer. Console scripts exist and `app` resolves from `/app`; a wheel
   would break `migration_paths()`, which reads `/app/migrations`.
3. The cache id is `portfolio-assistant-api-uv-py314`.
4. OCI labels (title, source, version, revision, created, licenses, description,
   documentation) come from `ARG VERSION`, `REVISION`, `CREATED`. No secret enters
   an `ARG` or `ENV`.
5. `api` runs `assistant-api` as UID 65532 with a stdlib HEALTHCHECK on `/readyz`
   (readiness: schema, corpus and graph, the same semantics the old image probed via
   `/health/ready`; `/healthz` stays the liveness endpoint for orchestrators).
   `worker` runs `assistant-knowledge-watch`; one-shot sync uses the same image.
6. `docker-bake.hcl` builds both targets (`linux/amd64`) with the same arguments.
7. `container-structure-test.yaml` and `container-structure-test.worker.yaml` assert
   user, port, command, labels and the Git/pip presence rules.

## Size

Before: 662.5 MB. Expected `api` about 560 MB (Git layer removed, lingua stays). The
500 MB budget is not reachable while lingua 2.2.0 stays a dependency. The ratchet is
set to the first measured value of the new `api` image in CI and recorded later in
`image.json`. Replacing the detector needs its own ADR and the golden language set.

## PostgreSQL

PostgreSQL stays on the Alpine 3.24 pgvector image per [ADR008](008-supported-postgres-base.md)
(Debian libxml2 blocker) instead of moving to trixie now.

## Consequences

- vps-ops runs migrations and retention with `api`, and knowledge sync and the
  watcher with `worker`. The two images share one source revision.
- hadolint, dockle, structure-test, Grype and building `worker` in CI follow after
  the CI rewrite merges.

## Confirmation

- `tests/test_container_layout.py`: stage names and order with `api` last, digest
  pins, repository-owned cache id without `vps-ops`, Git only in `worker`,
  `/readyz` healthcheck, labels, bake targets and structure-test contents.
- `uvx --from hadolint-py hadolint infra/docker/app/Dockerfile` with `.hadolint.yaml`.
- CI builds the image; the measured size is recorded after the first run.
