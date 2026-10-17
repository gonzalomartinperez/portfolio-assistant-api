# Toolchain and redacted secret verification — 2026-10-17

Scope: patch maintenance after main `fe5f665`. The task branch reconciles main ancestry
before changes, preserving the existing architecture, public API/SSE, private operations,
Python3.14.8, model policy and database versions. There are no migrations or provider calls.

uv0.13.1 and Ruff0.17.1 were verified through official PyPI metadata/release pages. Only
Ruff changed in the resolved Python graph. uv's reviewed OCI index is pinned in Dockerfile;
CI uses the same uv version. A temporary `uv tool run --python /usr/bin/python3 --from
uv==0.13.1 uv ...` invocation executed lock/sync checks without replacing global uv0.12.10.
These are stable tools, not declared LTS releases. Exact versions remain in the
[runtime baseline](../runtime-baseline.md), lock and Dockerfile.

Executed locally on WSL/Linux:

- Frozen uv installation passed; `ruff check`, `ruff format --check` and strict mypy passed.
- Offline suite: **423 passed, 27 integration tests deselected**, 8.48s.
- The added real-scanner fixture uses a disposable Git repository. It verifies current
  ignored-but-tracked markers, deleted historical markers and an unmerged branch, with
  nonzero status and redacted output. No actual credential is generated or inspected.
- `scripts.scan_secrets`: **832 reachable historical blobs**, zero known-pattern findings.
  This does not certify that all secrets, personal data or unreachable objects are absent.
- Contract export had no artifact drift; repository skills and workflow validation passed.

The existing full CI must verify the exact PR head, real PostgreSQL/Neo4j and production
image/security/proxy lifecycle before integration. Local Docker29.1.3 does not expose Buildx;
no unsupported legacy-builder substitution or new global plugin was installed. No local
full-image build or new live-model evaluation is claimed for this increment. CI image
results and current-head timings belong to the PR. There is no claimed application latency,
quality or VPS-capacity improvement from tooling patches.

No registry publication, deployment, secret rotation or visitor tracking is authorized by
this verification. Shared Coolify/proxy/retention execution remains vps-ops-owned.
