# Supported versions and upgrade policy

Checked 2026-10-12. Prefer an officially supported LTS line where the upstream offers
one. Otherwise use maintained stable releases and current security patches, with a
frozen lockfile and immutable image digest. Stable, LTS and security support are
different claims. Do not rename every dependency LTS or retain a vulnerable patch
because its major line is supported.

| Component | Selected line | Actual support policy / decision |
| --- | --- | --- |
| PostgreSQL | 18.6 | Official five-year major support; 18 ends 2030-11-14. PostgreSQL does not label releases LTS. |
| pgvector | 0.8.7 | Maintained stable extension, no formal LTS label; tested with PG 18.6. |
| Neo4j | 5.26 LTS | Retain the vendor-designated LTS line and review its security patches. |
| Python | 3.14.8 | Maintained stable release, not officially called LTS.3.15 remains blocked below. |
| uv | 0.13.0 | Stable pinned tooling; no formal LTS designation. |
| FastAPI, LangGraph, OpenAI SDK, psycopg | `uv.lock` | Maintained stable packages; no universal LTS policy. Review compiler/framework/auth changes manually. |
| OpenTelemetry Python | Stable SDK/OTLP APIs when adopted | No formal LTS; use manual allowlisted instrumentation and stable exporters. Avoid a beta exporter merely to get a badge. |
| Prometheus server | 3.13 LTS target | Supported until 2027-07-31; 3.5 LTS is already end-of-life. Selection/deployment belongs to vps-ops. |
| Grafana/collector | Reviewed maintained GA target | vps-ops must select exact supported editions/versions and digests; do not invent a universal OSS LTS guarantee. |

The independently owned backoffice pins Node 24 LTS and uses stable React/TypeScript
releases; their libraries do not all have an LTS program. Its owner maintains the
actual lockfile/runtime contract. No Redis, alternate model provider or other service
is added merely to increase the inventory. A complete application dependency graph
is recorded in `uv.lock`; image inventories include distribution/system packages.

## Python 3.15 decision

[Python 3.15.0](https://www.python.org/downloads/release/python-3150/) is a stable
release dated 2026-10-09. The exact interpreter installed successfully in an isolated
probe. Installing the existing locked dependencies with binary-only wheels failed:
`lingua-language-detector==2.2.0` has CP312/313/314 wheels, but no CP315 wheel. PyPI
reported 2.2.0 as the latest release on the inspection date. The current production
builder has no Rust toolchain and must not use forced ABI flags or patched vendor
source to conceal this gap. The owner explicitly accepted retaining 3.14.

Keep `.python-version`, `requires-python`, CI and the API image on 3.14.8. Revisit when
a stable compatible detector is available: freeze the new lock, replay supported/
unsupported language regressions, run real-service tests and smoke the non-root
production image. A successful interpreter download alone is not migration evidence.

## PostgreSQL 17 to 18

Never mount a 17 data directory in an 18 container or assume an image rollback can
read an upgraded store. The local Compose template uses a distinct `postgres18_data`
volume at `/var/lib/postgresql`; upstream PGDATA is `/var/lib/postgresql/18/docker`.
Use a fresh isolated Compose project when following the new demo instructions.
Older `postgres_data` volumes are preserved; none was deleted or converted here.

For existing data, vps-ops must rehearse encrypted backup/restore into a separate 18
store or a reviewed `pg_upgrade` procedure, check extensions and LangGraph schemas,
verify read/write/RAG/ownership, and select compatible app images before cutover.
Keep the 17 store until restoration and rollback criteria pass. The retained `deploy/`
stack is a historical transfer reference, not the current production authority.

## Maintenance gates

Record exact versions/digests, official support links, compatibility evidence and
remaining exceptions for every upgrade. Do not bypass required checks, install
nightlies or use force/legacy compatibility flags. Dependabot groups involving
frameworks, compiler/runtime changes or mixed risk require manual review. CI tests
the frozen install, boundaries/contracts, real services and image; release security
and production approval remain separate gates. Recheck dates before selecting a
release—an LTS label is not evidence that its support period is still active.

References: [PostgreSQL policy](https://www.postgresql.org/support/versioning/),
[pgvector](https://github.com/pgvector/pgvector),
[Neo4j LTS](https://neo4j.com/blog/developer/neo4j-v5-lts-evolution/),
[Prometheus LTS](https://prometheus.io/docs/introduction/release-cycle/),
[Grafana release stages](https://grafana.com/docs/release-life-cycle/).
