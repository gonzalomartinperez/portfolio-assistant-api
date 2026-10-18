# Application Docker layout and operations handoff

Date2026-10-18. Production ownership accepted by the vps-ops coordinator before
retiring the former stack/controller. Coolify with its one Traefik proxy remains
the selected platform. This change does not deploy, publish, migrate PostgreSQL17
or alter a shared volume. Production remains disabled.

## Current paths and commands

Run from repository root; supported release target is linux/amd64:

```sh
docker build --platform linux/amd64 -f infra/docker/app/Dockerfile -t portfolio-assistant-api:local .
docker build --platform linux/amd64 -f infra/docker/postgres/Dockerfile -t portfolio-assistant-postgres:local .
docker compose -f infra/compose/local.yaml -p assistant-local config --quiet
```

Each actual recipe has an adjacent Dockerfile.dockerignore and a narrow deny-default
context. The root .dockerignore is a deny-all fallback; there is no root recipe.
Application COPY inputs, runtime paths, SQL bytes, users, images/digests, ports and
resource settings remain unchanged. The PostgreSQL recipe copies the relocated
public bootstrap/HBA files into their existing /usr/local/share/portfolio-postgres
paths. No wrapper recipe or empty directory is invented for the pinned Neo4j
vendor image. Its security acceptance remains a separate release blocker.

Local Compose resolves ../.. to the repository root and uses an explicit recipe
path. Its explicit portfolio-assistant-local project name prevents sibling
infra/compose directories from sharing Compose defaults; -p can override it for
an isolated test. Existing volumes are not renamed, migrated or removed.
Always select its file and a project name; do not run generic compose/down
against another agent's environment. CI and Dependabot consume the new locations.

## Retirement and preserved responsibilities

- Retired: deploy/compose.yaml, deploy/apply-release.sh,
  deploy/nginx/server.conf and .github/workflow-templates/deploy-vps.yml.
  Their source remains in the previous Git revisions; no application-side
  production controller or separately editable production stack replaces them.
- Four active local Nginx smoke resources move from deploy/nginx to
  tests/fixtures/proxy. They are a CI test fixture, not a deployment proxy.
- Active public PostgreSQL bootstrap/HBA resources move beside their recipe;
  runtime/knowledge-worker grants and migrations remain application-owned.
- Safe environment examples remain references, not secret delivery configuration.
- vps-ops must review the new paths when refreshing source fingerprints/build
  procedures. It selects compatible immutable image digests; a merge never silently
  changes its runtime pins. The app does not rebuild source on the VPS.

## Verification and limits

Regression tests check explicit CI recipe selection, Compose context resolution,
separate ignore files, unchanged bootstrap/HBA checksums, root-path retirement and
absence of a competing controller. Local Compose config and workflow linting are
non-starting checks. Full PR CI must build both images, scan them and exercise real
services, active-stream termination and proxy behavior before integration.

Current production runtime semantics remain in [deployment contract](deployment-contract.md).
No new paid model call, registry publication, remote deployment, DNS edit, Neo4j
waiver or VPS resource/performance guarantee is implied.

Official references checked for this implementation:
[Docker build contexts and per-recipe ignore precedence](https://docs.docker.com/build/concepts/context/)
and [Compose relative build context](https://docs.docker.com/reference/compose-file/build/).

Local implementation checks:676offline tests passed (37real-service cases excluded),
27.44s;20focused layout/security-descriptor/release tests passed0.63s; after adding
an explicit fallback Compose project name,5layout tests passed0.10s. Existing
fixture-env exports still override the fallback; no change to selected fixture
project/volumes is implied. Ruff, skill validation, workflow lint and non-starting
Compose configuration pass. Source-only independent review found no P1/P2; actual
Docker build/scans and runtime smoke remain required in this increment's CI.
