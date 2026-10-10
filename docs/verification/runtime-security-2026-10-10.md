# Runtime security increment · 2026-10-10

Application-owned patch verification under WSL Linux amd64; no publication, main
promotion or production deployment. Source is the commit containing this report.

Python 3.14.8 replaces the older 3.14 image within the supported project line;
Neo4j 5.26.31 Community replaces 5.26.17 within the LTS line. Registry manifests
were verified before pinning. PostgreSQL 17 / pgvector 0.8.1 remain unchanged.
The frozen dependency lock is unchanged. uv 0.12.10 could not download the new
Python patch; reviewed uv 0.13.0 provisions it successfully. CI and Docker use
0.13.0. This is not an unsupported interpreter fallback or a global installation.

The original scanner findings for msgpack/setuptools/older urllib3 were traced to
base-interpreter pip vendoring, outside the application venv. They were real
installed artifacts, not dismissed as metadata false positives. Runtime does not
need an installer: pip is properly uninstalled and ensurepip removed only in the
final stage; the build stage and frozen installation retain their tools. Container
smoke checks absence using the base interpreter, not only the application venv.

The complete Trivy 0.75.0 candidate report contains 0 CRITICAL, 58 HIGH, 87 MEDIUM,
103 LOW and 9 UNKNOWN findings. No HIGH has a fixed version in this database. Four
fixable HIGH findings disappeared after removing installer bundles. There is no
ignore file, patched scanner database or blanket exception. These unresolved OS
findings remain a production-assessment blocker. CI now retains the complete
image inventory and adds a gate for all CRITICAL and fixable HIGH findings, with
schema/OS-inventory/image-ID validation and fail-closed error behavior. A green
remediation gate is not production approval.

A real active-stream SIGTERM probe exposed intermittent lifecycle ordering: the
ASGI request can be cancelled before nested generators register their cleanup.
The previous drain handled only registered tasks. RunService now also tracks
active run IDs and schedules their idempotent interruption before closing storage.
A deterministic regression exercises lifespan cleanup before generator finalization.
Container logs are retained as bounded fixture diagnostics before container removal.

Before that final shutdown regression, 288 tests passed in 17.26 seconds on Python
3.14.8 with isolated real PostgreSQL/Neo4j. Strict mypy (23 files), Ruff, format,
contract drift, Compose and skill validation passed. Further final image/CI results
are recorded below after execution. Earlier timing is not a measured speedup.

The local image before the final cleanup change was 271,704,695 bytes, versus
273,165,713 bytes for the previous runtime increment: roughly 1.46 MB removed.
Neither local image IDs nor locally generated manifests are published registry
digests. No field performance or VPS resource guarantee is inferred.

References: [Python 3.14.8 security release](https://www.python.org/downloads/release/python-3148/),
[uv Python selection](https://docs.astral.sh/uv/concepts/python-versions/),
[Neo4j 5.26 changelog](https://github.com/neo4j/neo4j/wiki/Neo4j-5.26-changelog),
[Neo4j minor upgrade procedure](https://neo4j.com/docs/upgrade-migration-guide/current/version-5/upgrade-minor/).

No production-store upgrade/restoration, effective Coolify/proxy/TLS header test,
real OAuth, physical device or actual backoffice operations integration is claimed.
vps-ops selects compatible digests and owns production operations. Existing
deploy/ templates remain transfer references, not competing production authority.

Final local suite: **289 passed in 16.75 seconds**, including 25 real-service
integration cases and 15 image-policy cases. Final candidate image ID:
`sha256:9880c589a7473e5fdbbf8f7db7e7abc6c5cfa2c9102c3990776850ee2c9521e2`,
size **271,704,822 bytes**. Its full scan retains the same 257 findings and passes
the added remediation gate with 0 critical / 0 fixable high / 58 unresolved high.
Raw local artifacts are ignored under `artifacts/security-20261010/`; CI retains
the full report, policy summary and bounded fixture-container logs.
