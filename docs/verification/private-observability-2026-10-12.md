# Private observability verification · 2026-10-12

This report separates application verification from production monitoring and
paired browser acceptance. No additional paid model call was made for this work.

## Implemented and checked

Private v1 status JSON and Prometheus exposition require a dedicated bearer token,
reject invalid/unconfigured access safely and exclude shared caching. Application
measurements contain opaque unrelated trace IDs, bounded named phases/outcomes and
server first-fragment latency. The model has no content, credentials or visitor IDs.

An actual loopback HTTP/protobuf receiver decoded manual OTLP traces and metrics.
Assertions checked the exact service resource, phase names, trace identity and
absence of question/prompt/session/credential fields. Other tests cover vendor
header hooks, redirect prohibition, safe SDK diagnostics, bounded queues, exporter
failure independent from durable storage, cross-task generator cancellation and
shutdown after a failed in-progress SQL write. Framework request telemetry is
explicitly disabled; a global exporter regression checks requests produce no spans.

Local full suite after the final cancellation/token assertions: **346 passed in
96.83 seconds**, including 26 real PostgreSQL/Neo4j integration tests. Focused
observability suite: **22 passed in 14.60 seconds**. Timing varies with concurrent
local work; these are measured runs, not a performance improvement claim.

An earlier run exposed a cold operational pool timeout and returned safe 503. The
private pool checkout allowance was increased from 100 to 500 ms while maintaining
the four-second HTTP deadline; the endpoint assertion stayed strict. The first OTLP
trace-ID assertion also required decoding protobuf JSON's base64 representation,
rather than comparing it directly to hexadecimal. Neither failure was waived.

## Clean snapshot and frontend compatibility

An isolated tracked archive of `79d8dc9e05752bf60ab22dcf3af863968e8a053f` installed
with uv 0.13.0 and `uv sync --frozen`, then passed Ruff, strict mypy, skills and
**319 offline tests / 26 integration deselections in 29.25 seconds**. Generated
contracts matched committed bytes. The first final comparison used system Python
without dependencies and failed to import Pydantic; repeating with the isolated
venv verified the bytes. No credentials or ignored working-tree files entered it.

The committed backoffice HTTP adapter and runtime validator from
`618aa914ced48bf08ba8d613537ecd28ef797d5e` executed under Node 24.21.0 against actual
local API HTTP responses. They accepted the snapshot and rejected invalid bearer
credentials with the authorization state. This exercised no OAuth/browser session
or deployed UI. Local diagnostic evidence is in ignored
`artifacts/backoffice-contract-20261012/`. An initially occupied local port was
abandoned without stopping its owner; the verified service used isolated 58237.

## GitHub/container evidence

PostgreSQL PR #46 passed Actions `38289478519` and merged at
`2e951faa25b5ebe0d15e8642f9cbb4e6e2e35527`. PostgreSQL 18.6/pgvector 0.8.7 uses a fresh
volume; no older data was upgraded or deleted. Neo4j remains the available verified
5.26.31 LTS image. The proposed 5.26.32 tag was unavailable.

Operations PR #47 source `79d8dc9e05752bf60ab22dcf3af863968e8a053f` passed Actions
`38291944927`: static/offline 41 seconds, real-services/container 215 seconds,
aggregate gate 4 seconds. That run verified non-root normal SSE, active-stream
SIGTERM and fixture-proxy path/CORS/disconnect behavior. Final follow-up changes
require their own current-head gate before merge; this run is not substituted for it.

The run's API scan reported zero critical, zero fixable high and 58 unresolved high
findings; PostgreSQL reported three critical without listed fixes and no fixable
critical/high findings. These are separate from release approval. PostgreSQL's
critical package inventory included libsqlite3-0, libxml2 and zlib1g. Do not remove
runtime libraries or suppress findings merely to obtain a clean label.

Instantaneous local idle/post-test samples: PostgreSQL 44.41 MiB of its 512 MiB
limit; Neo4j 670.5 MiB of its 1.5 GiB limit. They are not peak/load or VPS capacity
measurements. PostgreSQL's base is Debian 12 LTS; API/Neo4j use Debian 13. Support
policy records actual upstream lifetimes and beta transitive exceptions.

## Remaining owner gates

vps-ops owns effective private proxy/egress, collector/Prometheus/Grafana selection,
OAuth/dashboard pairing, retention scheduling, measured KVM 4 resources, encrypted
backup/restore and compatible rollback. Model availability is not inferred from
store readiness; usage is an estimate with incomplete historical token coverage.
No main promotion, publication, deployment or portfolio assistant activation occurs.
