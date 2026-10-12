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

## Final application acceptance

PR #47 passed final code revision `017df0c3036a3a976cf3b016b783f2932be31d7d` in
Actions `38293707505`: static/offline 30 seconds, real-services/container 186 seconds,
aggregate gate 4 seconds. It merged into develop at
`8d411d76699c98e512f07127af371e2b6305fd57`. The added non-UTC connection regression
passed separately; ledger reservations and snapshot aggregation now explicitly
truncate the calendar month in UTC, independently of database session timezone.

Local final production image ID:
`sha256:5d33ab1db6178f930f5860cd70f27b766609812615a20e49c85f4f3182fc3bc6`.
It is an engine image ID, not a published registry manifest digest. Runtime source
hashes matched the final operations/ledger/bootstrap files. Size: 272,623,078 bytes;
the earlier same-environment baseline was 271,706,379 bytes, a 916,699-byte increase
(about 0.34%). This is container size, not browser bundle or model-quality performance.

The image passed normal SSE and active-stream SIGTERM smoke. A separate private
Compose-network fixture used the image's default startup command, its actual Docker
healthcheck, read-only filesystem, UID 65532, dropped capabilities, 512 MiB memory,
one CPU and 128 PID limits. Readiness and authenticated status returned 200, missing
bearer returned 401, Prometheus exposition and no-store headers passed, and Docker
reported healthy. Only the owned test container was stopped/removed; volumes remain.
The first cold image build downloaded Lingua's 162.4 MiB wheel slowly; the final cached
build reused dependencies. No build-time secrets or alternate production stack were added.

This verifies application artifact/runtime readiness in local Linux fixtures and
GitHub CI. Residual database/vendor vulnerabilities, real OAuth/browser pairing,
collector deployment, backup/restore and actual VPS acceptance remain open owner gates.

## Dependabot final compatibility gate

Native Dependabot replaced the conflicted PR #44 with PR #48 after the target
advanced; no human work was force-pushed. All 14 changes were reviewed, including
FastAPI's new native telemetry and Neo4j driver 6.4.0. Source
`95c94291453ce6152de21a6b9748c410f367f3c9` passed frozen install, Ruff, strict mypy,
**347 local tests in 69.93 seconds** and unchanged exported contracts.

Actions `38295075616` passed static/offline in 35 seconds, real-service/container
in 239 seconds and the required aggregate gate in 3 seconds. The exact verified
head merged at `5ff96d3dbd015ddf9f90f83231052f57b7d494c8`. This was an authorized
manual review/merge, not eligibility for unattended dependency automation. The
live voice evaluation remains evidence for its recorded earlier SDK revision;
no paid model replay was made for this dependency refresh. Current container and
provider-adapter tests are deterministic, not another live OpenAI evaluation.

After dependency integration, the committed backoffice adapter was replayed against
actual local HTTP from API revision `5ff96d3dbd015ddf9f90f83231052f57b7d494c8` under
Node 24.21.0: valid status mapped to available; invalid bearer mapped to authorization
failure. The runtime `api_commit` matched that revision. This still does not claim
browser/OAuth or deployed dashboard acceptance.
