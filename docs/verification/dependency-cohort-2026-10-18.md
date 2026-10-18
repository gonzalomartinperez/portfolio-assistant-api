# Reviewed dependency cohort · 2026-10-18

This is a manually reviewed, finite cohort, not automatic approval of dependency
updates. Authenticated PR metadata identified Dependabot user49699333, the same
source repository and develop target. The original commits are preserved in the
cohort ancestry; no human changes were added to their branches.

| Original PR / head | Complete impact |
| --- | --- |
| 96 / 220e7bc127ac409e4996397dda844cd0633aef98 | iniconfig2.3.0→2.3.1, pytest-only transitive package; version/artifact entries only |
| 97 / 624fcfb5e2481661a282589ddddc2f1d484b9cee | setup-uv10.2→10.3, exactly three immutable action pins; uv0.13.1, caches and permissions unchanged |
| 98 / ac1aab5018fe6e423978ecb5b30dad60bac7de65 | jsonpatch1.33→1.35, jsonpointer3.1.1→3.2.1, orjson3.12→3.13, tenacity9.1.4→9.2.1; version/artifact entries only |

The semantic lock comparison found no added/removed packages, registry switches,
dependency-edge changes or top-level lock configuration changes. This does not
make runtime changes harmless. JSONPatch changes JSON equality, nested moves,
scalar/root operations and malformed-input handling; jsonpointer changes string
indexing and assignment validation. Tenacity changes retry/wait/context behavior.
The application does not enable automatic generation retries. orjson retains
CPython3.14 Linux wheels and drops Windows32, which is not a supported deployment.

Reviewed upstream sources: [iniconfig changelog](https://github.com/pytest-dev/iniconfig/blob/v2.3.1/CHANGELOG),
[setup-uv10.3](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.0),
[JSONPatch1.34](https://github.com/stefankoegl/python-json-patch/releases/tag/v1.34),
[JSONPatch1.35](https://github.com/stefankoegl/python-json-patch/releases/tag/v1.35),
[jsonpointer3.2](https://github.com/stefankoegl/python-json-pointer/releases/tag/v3.2.0),
[jsonpointer3.2.1](https://github.com/stefankoegl/python-json-pointer/releases/tag/v3.2.1),
[tenacity9.2](https://github.com/jd/tenacity/releases/tag/9.2.0),
[tenacity9.2.1](https://github.com/jd/tenacity/releases/tag/9.2.1) and
[orjson3.13](https://github.com/ijl/orjson/blob/3.13.0/CHANGELOG.md).

Original PR98 run39093623802 failed during fresh PostgreSQL fixture bootstrap,
before its application assertion. The same failure occurred on develop without
these upgrades. Neither failure is waived or attributed to dependencies without
proof. The cohort starts from corrected developa5707b24bf1853e44b9888794bcfb7575e462cea;
[the readiness regression](postgres-startup-2026-10-18.md) preserves the RED and
records the independent fix. Every paired job must pass on the combined cohort.

Verification includes the frozen lock, offline application/architecture/runtime
compatibility tests, actual SDK mock transport and single-attempt cancellation
coverage, real LangGraph checkpoints/cleanup and HTTP/SSE, bilingual fixtures,
restricted IAM/recovery and production image scans/smokes. Model quality and live
OpenAI performance are not tested by this dependency increment. No paid calls,
production activation, image publication or deployment are authorized here.

Local combined-cohort result: frozen uv0.13.1 installation succeeded on CPython3.14.8;
696 offline tests passed (38 service tests deselected) in14.35seconds. Ruff checks,
formatting, configured strict mypy and contract drift passed. Hosted real-service
and image acceptance remains a separate required gate on this exact candidate.
