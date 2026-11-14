# Dependencies

Policy (ecosystem section 7, [10](research/10-standards-dependencies.md) "Dependency policy template"): a new runtime dependency needs an ADR with need versus platform, health (Scorecard and deps.dev), licence allow-list (MIT, Apache-2.0, BSD, ISC, 0BSD, BlueOak), cost, maintainer count and exit cost. Dev, test and CI tools are not distributed in the image and use a lighter check (licence recorded, pinned, in a dependency group). **Licence column verified on 2026-11-14 (M1-10)** from the installed wheel metadata (`License-Expression`, classifiers) of the locked versions and from deps.dev; section 6 holds the evidence. `scripts/check_license.py` checks only this repository's own MIT licence, so it is not a third-party licence audit.

Weekly single-PR rule applies to all of them (one grouped PR). Exact pins are kept only where a pin has a reason.

## 1. Current runtime dependencies (`pyproject.toml`)

| Package (constraint) | Purpose | Main alternative | Cost and notes | Licence | 2026 health and security | Decision |
|---|---|---|---|---|---|---|
| `fastapi >=0.143.3` | HTTP and SSE | Starlette directly, Litestar | Core framework; native SSE since 0.135 | MIT | Very active | Keep |
| `uvicorn >=0.54.0` | ASGI server | Hypercorn, Granian | Needed; flags `--no-proxy-headers` are part of the deploy contract | BSD-3 | Active | Keep |
| `pydantic >=2.14.1,<3`, `pydantic-settings >=2.16.0` | Models and settings | dataclasses plus attrs | Boundary validation | MIT | Very active | Keep; settings move to `SecretStr` |
| `langgraph >=1.2.16,<2`, `langgraph-checkpoint-postgres >=3.1.2,<4`, `langchain-core >=1.6.12,<2` | Run workflow with durable checkpoints | Hand-written state machine | Checkpoint tables in PostgreSQL, cancellation semantics tested | MIT | Active, frequent releases | Keep; checkpoint retention covered by integration tests |
| `langsmith ==0.14.9` | Pulled by `langchain-core`; exact pin to control the transitive version | Remove explicit pin | Tracing is refused by the settings validator; the SDK stays dormant | MIT | Active | Keep for now; try dropping the explicit pin in M4 if `uv tree` shows it is only transitive and tests prove tracing stays off |
| `openai >=3.33.0` | Responses API and embeddings, opt-in | Anthropic SDK, litellm | One provider, no fallback by design | Apache-2.0 | Active | Keep |
| `neo4j >=6.4.1,<7` | Graph projection and read queries | `gqlalchemy`, Postgres graph | Needs a Neo4j container; vendor findings open (2026-10) | Apache-2.0 AND Python-2.0 | Active | Keep pending PAA-D12 spike |
| `psycopg[binary,pool] >=3.3.6` | PostgreSQL and pgvector access | asyncpg | Required by the LangGraph Postgres checkpointer; binary wheels | **LGPL-3.0-only** (also `psycopg-binary`, `psycopg-pool`) | Active; Scorecard 4.1 | Keep; licence exception recorded in [ADR009](../adrs/009-psycopg-lgpl-exception.md) (unmodified library, MIT application; asyncpg cannot replace the checkpointer dependency) |
| `lingua-language-detector ==2.2.0` | Language detection (EN, ES, unsupported) | `fasttext-langdetect`, `langdetect`, heuristic | Large wheel with models; suspected main share of the 992 MB image **[hypothesis]** | Apache-2.0 | Active | Keep; measure image share in M1; restrict languages or replace only if golden language items stay 100% |
| `opentelemetry-sdk >=1,<2`, `opentelemetry-exporter-otlp-proto-http >=1,<2` | Opt-in private tracing and metrics | none | Off by default (`otel_sdk_disabled`) | Apache-2.0 | Active | Keep; centralize `gen_ai.*` attributes in one module |
| `prometheus-client >=0.22,<1` | Private `/metrics` | OTel metrics only | Overlaps with OTel; small | Apache-2.0 AND BSD-2-Clause | Active | Keep; revisit in M4 whether OTel metrics make it redundant |

## 2. Current dev dependencies

| Package | Purpose | Decision |
|---|---|---|
| `pytest >=9.1.1` | Test runner | Keep |
| `httpx >=0.28.1` | Test client and Locust client | Keep |
| `mypy >=2.4.0` | Strict typing gate | Keep |
| `ruff >=0.17.1` | Lint and format | Keep; families extended |
| `pyyaml ==6.0.3` | Workflow and compose validation scripts | Keep; used by tooling only |

## 3. Proposed additions (dependency groups; none enters the image)

| Package | Group | Purpose | Alternatives considered | Licence | Cost and risk | Decision |
|---|---|---|---|---|---|---|
| `ranx` | `eval` | Recall@k, nDCG, MRR, paired significance | `ir-measures`, `pytrec_eval`, hand-coded metrics | MIT | Pulls numpy and numba (install weight); eval group only | Adopt (ecosystem 12.3) |
| `hypothesis` | `dev` | Property-based and stateful tests | `fast-check` n/a | MPL-2.0 | Dev only, never distributed; MPL file-level copyleft not triggered | Adopt (ecosystem 11) |
| `pytest-randomly`, `pytest-xdist`, `pytest-benchmark`, `pytest-asyncio`, `time-machine` | `dev` | Order randomization, parallelism, benchmarks, async tests, frozen time | `freezegun` (slower), `pytest-repeat` | BSD, MIT, BSD, Apache-2.0, MIT | Small | Adopt |
| `coverage[toml]`, `diff-cover` | `dev` | Branch and diff coverage | `pytest-cov` wrapper | Apache-2.0 | Small | Adopt |
| `mutmut` (3.x) | `dev` | Mutation testing | `cosmic-ray`, `mewt`, `muton` | BSD-3 | Python 3.14 support unverified: spike M2 (PAA-D19) | Adopt after spike |
| `import-linter` | `dev` | Layer contracts | AST guard only | BSD-2 | Small | Adopt (ecosystem 9) |
| `vulture` | `dev` | Dead code | `ruff` rules only | MIT | False positives need an allowlist | Adopt |
| `schemathesis` | `dev` | OpenAPI fuzzing | `dredd`, `restler` | MIT | Heavier install; nightly long run | Adopt |
| `locust` | `load` | SSE load through an httpx client | `k6` with xk6-sse, Artillery | MIT | Gevent footprint; separate group | Adopt (one half-day spike to confirm streaming client; research [04] section 11) |
| `jsonschema` | `dev` | Example and schema validation | `fastjsonschema` | MIT | Small | Adopt |
| `pytest-recording` / `vcrpy` | `dev` | Transport adapter tests only | own recorder (used for the golden lane) | MIT | HTTP cassettes are brittle across SDK bumps | Adopt for transport tests only (S3) |
| `numpy` | `eval` | Load the frozen embedding snapshot | none | BSD-3 | Transitive via ranx | Via ranx |

## 4. CI and container tools (pinned binaries or SHA-pinned actions, not Python dependencies)

| Tool | Use | Note |
|---|---|---|
| oasdiff | Breaking-change detection | Go binary pinned by checksum |
| Schemathesis, Locust, OWASP ZAP | Fuzz, load, DAST | ZAP API scan in a pinned container, nightly |
| Grype, Syft | Image scan, CycloneDX SBOM | Trivy only as SHA-pinned binary at or after v0.35.0 (E8); the current v0.75.0 download with a checked SHA-256 satisfies it |
| zizmor, actionlint, gitleaks, osv-scanner, CodeQL, dependency-review, Scorecard | Workflow and supply-chain security | Shared reusable workflows |
| hadolint, dockle, container-structure-test | Dockerfile and image checks | |
| lychee, markdownlint-cli2, Vale | Docs | Vale on English prose only |
| release-please | Release PR, changelog, tag | Needs a GitHub App token (owner grants) |
| garak or promptfoo (optional, weekly sweep) | Live red team | promptfoo is OpenAI-owned since 2026 ([03] section 17): pin if used; the in-repo attack pack is the default |

## 5. Considered and rejected

| Candidate | Reason |
|---|---|
| Pact | Both consumers are first-party; oasdiff plus schema compile is enough (ecosystem 11.1) |
| DeepEval and RAGAS as a gate | Uncalibrated LLM metrics; allowed only as optional diagnostics, never gating |
| Arize Phoenix | Elastic License 2.0 and no evidence of need |
| Langfuse, LangSmith hosted datasets | Tracing is off by design; Langfuse (MIT) is the exit option if hosted viewing is ever wanted (PAA-D8) |
| Local cross-encoder reranker (about 500 MB) | About 76 chunks and a shared VPS; reconsidered only if Recall@5 stays below 0.90 after H1 to H5 |
| DI framework | Ecosystem 9: composition root in lifespan is enough |
| Shared `assistant-kit` runtime package with the sibling API | Premature; revisit when three modules are byte-identical across repos (PAA-D20). Scaffolding parity comes from `engineering-standards` templates |
| k6 | No native SSE; Locust chosen |
| cspell (Node) | Adds Node to a Python repo; an in-repo regex lint covers the Spanish rule |

## 6. Verification evidence (2026-11-14, M1-10)

Locked versions on `develop` at `45c6923`; licence from wheel metadata, cross-checked with deps.dev (`api.deps.dev/v3`); OpenSSF Scorecard is the deps.dev project score (blank when deps.dev has none).

| Package | Locked | Licence (metadata) | deps.dev licence | Scorecard |
|---|---|---|---|---|
| fastapi | 0.162.0 | MIT | MIT | |
| uvicorn | 0.54.0 | BSD-3-Clause | BSD-3-Clause | |
| pydantic / pydantic-settings | 2.14.2 / 2.16.2 | MIT | MIT | 6.8 / |
| langgraph / langgraph-checkpoint-postgres | 1.2.19 / 3.2.0 | MIT | MIT | |
| langchain-core | 1.7.4 | MIT | MIT | 5.9 |
| langsmith | 0.14.9 | MIT | MIT | 8.7 |
| openai | 3.42.1 | Apache-2.0 | Apache-2.0 | 7.8 |
| neo4j | 6.4.1 | Apache-2.0 AND Python-2.0 | same | 7.0 |
| psycopg / psycopg-binary / psycopg-pool | 3.3.6 / 3.3.6 / 3.3.3 | LGPL-3.0-only | LGPL-3.0-only | 4.1 |
| lingua-language-detector | 2.2.0 | Apache-2.0 (classifier) | non-standard (metadata has no SPDX field) | 2.8 |
| opentelemetry-sdk / exporter-otlp-proto-http | 1.45.2 | Apache-2.0 | Apache-2.0 | 8.2 |
| prometheus-client | 0.26.0 | Apache-2.0 AND BSD-2-Clause | same | 6.6 |

Transitive packages outside the allow-list (scan of every installed distribution): `typing_extensions` PSF-2.0; `certifi`, `pathspec` MPL-2.0; `orjson` MPL-2.0 AND (Apache-2.0 OR MIT). All are used unmodified; MPL-2.0 is file-level copyleft and applies only to modified files, so no exception is needed (ADR009 consequences). Dev tools (not in the image): httpx BSD-3-Clause, mypy MIT, pytest MIT, pyyaml MIT, ruff MIT. Low Scorecard values (lingua 2.8, psycopg 4.1) are recorded for the M4 dependency review, not as blockers.
