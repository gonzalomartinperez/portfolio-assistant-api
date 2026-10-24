# Research: proposed dependencies

Planning research only. Adding any of these follows the
[dependency policy](../../dependency-updates.md) and its own ADR with measured CI cost
(see [roadmap risks](../roadmap.md#cross-phase-risks)). The owner allows any library
that is justified; this list is the justification baseline, not an approval.

Development dependencies unless stated otherwise. Version: pin the current stable
release at adoption time (the 7-day Dependabot cooldown is already configured).

| Library | Purpose | Cost | License | Health / note |
|---|---|---|---|---|
| pytest-xdist | unit parallelism | 0 | MIT | pytest-dev, active |
| coverage[toml] / pytest-cov | branch coverage, sysmon | 0 | Apache-2.0 / MIT | active |
| diff-cover | coverage on new lines | 0 | Apache-2.0 | active |
| hypothesis (+ hypothesis-jsonschema) | property-based, stateful | 0 | MPL-2.0 | very active |
| schemathesis | OpenAPI fuzz/contract | 0 | MIT | active |
| mutmut 3.x | mutation testing | nightly CPU | BSD-3 | v3.5.0 Feb-2026 |
| testcontainers | local integration with real databases | 0 | Apache-2.0 | active |
| httpx-sse | SSE client in tests/load | 0 | MIT | small, stable |
| locust | load testing | 0 | MIT | active |
| ranx | IR metrics (Recall, nDCG, MRR) | 0 | MIT | active, numba |
| vcrpy / pytest-recording | provider cassettes for regression | 0 | MIT | active |
| promptfoo (Node, pinned `npx`) | OWASP LLM red team | 0 offline; live with a cap | MIT | OpenAI since Mar-2026, OSS maintained |
| osv-scanner or pip-audit | vulnerabilities in `uv.lock` | 0 | Apache-2.0 | Google / PyPA |
| gitleaks | secrets | 0 | MIT | active |
| oasdiff | OpenAPI breaking changes | 0 | Apache-2.0 | active |
| syft (or Trivy SBOM) | SBOM | 0 | Apache-2.0 | Anchore |
| just | task runner | 0 | CC0 | stable |
| pre-commit (or prek) | local hooks | 0 | MIT | stable |
| Runtime: none new | — | — | — | `unaccent` is a PostgreSQL extension (contrib) |
| Optional: self-hosted Langfuse | trace/eval UI | VPS infrastructure | MIT | ClickHouse since Jan-2026 |

Rejected: Pact (overkill with 2 own consumers), DeepEval/RAGAS as a gate (uncalibrated
LLM metrics; use only as a reference), local cross-encoder (no evidence of need),
Phoenix (ELv2).
