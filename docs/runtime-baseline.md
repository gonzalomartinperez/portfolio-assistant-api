# Runtime baseline acceptance — 2026-10-17

The owner authorized execution of the shared deployment-readiness plan. This repository owns
its code, tests, image and runtime contract. The private vps-ops inventory owns the shared
baseline/routing/release policy; Coolify remains the sole deployment executor.

| Applicable component | Exact committed lock version |
| --- | --- |
| `fastapi` | `0.143.3` |
| `uvicorn` | `0.54.0` |
| `openai` | `3.33.0` |
| `pydantic` | `2.14.1` |
| `pydantic-settings` | `2.16.0` |
| `opentelemetry-sdk` | `1.45.1` |
| `mypy` | `2.4.0` |
| `ruff` | `0.17.1` |
| `pytest` | `9.1.1` |

The lockfile is authoritative for the complete dependency graph. This dated view does not
assert that these versions remain the newest forever or that an image has been published.
Python3.14.8 is maintained stable, not named LTS; uv0.13.1 is stable tooling. These are this repository’s verified versions; other applications adopt their own committed, tested baseline. Portfolio alone needs Lingua2.2.0 (no CP315 wheel), LangGraph/LangChain1.x LTS, pgvector and Neo4j. Other projects own and verify their own storage/provider adaptations; no cross-project runtime guarantee follows from this table.

## Image and operations boundaries

Build dependencies are isolated from the runtime. Frozen installs and dependency-cache mounts
reduce repeated downloads; cache content is not copied into the runtime. Dockerfile frontend
and image bases are digest-pinned. Private registry visibility and immutable release manifests
remain prerequisites for publication and deployment; local image identifiers are not registry
provenance. Images are built in application verification, never rebuilt on the VPS.

The HTTP image uses UID65532, a read-only root with its declared writable paths and an exec-form Python probe. No new provider calls, accounts, network service or model-budget setting is introduced. OpenTelemetry stays opt-in; FastAPI0.143 changes automatic exporter setup to opt-in. This matches the explicit exporter policy rather than enabling ambient hooks.

Databases and writable data stay isolated by project. Secret values are excluded from Git,
images, source build arguments and diagnostics. Runtime credentials are delivered by Coolify;
recovery credentials remain independently available. Existing public websites stay on Business
and their assistant activation remains deferred. No deployment trigger is enabled.

The PostgreSQL18.6/pgvector0.8.7 maintained-base candidate is recorded separately
in [ADR008](adrs/008-supported-postgres-base.md). Its Alpine3.24 main support ends
2028-06-01, independently of PostgreSQL's major support window. The current source
candidate changes neither Python/Node nor the application/Neo4j base. Exact-image
and dual-database recovery acceptance remain prerequisites; this dated baseline
does not select a production image or waive the previous Debian critical finding.

## Verification and remaining gates

Frozen installation, formatting/linting, typing, unit/contract checks and fixture-mode verification were run locally. No paid provider call or real key was used. Exact-image and real-service/restore evidence must accompany the release; migration rollback is separately reviewed.

See [deployment contract](deployment-contract.md) for ports, health, secrets, data and shutdown.
The shared baseline does not promise zero downtime, production capacity or an advisory-free
image. Current unfixed OS findings remain visible; no package is removed or scanner weakened
merely to change a vulnerability count.

The [October 18 exact-image inventory](verification/container-security-2026-10-18.md)
records the current package findings and the explicit LZMA security pin. Historical
image results remain attached to their original identities; patched images need a rescan.

## CI privacy boundary

Public-repository CI runs synthetic checks without publishing images, raw diagnostic artifacts
or browser reports. Review results in the bounded redacted job output. Private release artifact
publication needs a separately accepted access/visibility path; passing CI never activates it.

## October 17 patch review

The patch increment selects [uv0.13.1](https://github.com/astral-sh/uv/releases/tag/0.13.1)
and [Ruff0.17.1](https://github.com/astral-sh/ruff/releases/tag/0.17.1), confirmed through
the official PyPI version metadata. uv remains build/CI tooling; it is not copied into the
HTTP runtime. The Dockerfile pins its OCI index digest; Ruff is the only changed resolved
Python package. Neither tool has a declared LTS channel. Python, model, database engines,
wire contracts and operational payloads remain unchanged. See
[verification](verification/toolchain-security-2026-10-17.md) for executed checks and limits.

## Fixed runtime compatibility review — October 17, 17:35 UTC

Reviewed the explicit cohort FastAPI0.143.3, OpenAI3.33.0, pydantic-settings2.16.0,
LangGraph1.2.16, LangChain Core1.6.12 and Neo4j driver6.4.1. LangSmith0.14.9 is the
minimum required transitive update for Core and remains tracing-disabled; the resolver's
optional0.14.11 selection was not retained. No checkpoint, database engine, image base,
model, pricing or public/private contract change is part of this cohort. The older
October17 toolchain result remains historical evidence. See
[runtime compatibility evidence](verification/runtime-compatibility-2026-10-17.md).

Subsequent to the immutable v1.1.0 tag, the
[manual synthetic-summary exporter](synthetic-evaluation-export.md) promotes the
same LangSmith0.14.9 to a direct dependency; all 79 resolved package names/versions
remain identical. This is source behavior after the cohort above, not an SDK upgrade
or activation of global tracing. Record the actual later source commit in any release
manifest; do not relabel or move the existing tag.
