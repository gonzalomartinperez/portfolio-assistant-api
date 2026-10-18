# Site experience contract freeze · 2026-10-18

Scope: offline shared vocabulary and a closed Portfolio profile, not a new public
endpoint, collector, persistence migration, report UI or production activation.
See [semantics and ownership](../site-experience-contract.md).

| Artifact | SHA256 |
| --- | --- |
| `site-experience-v1.schema.json` | `355341ceb79621bcb6d0ac79fb211b78958436b1e89f8bee8a3a78953ece5f59` |
| `site-experience-portfolio-v1.schema.json` | `f5905c368e668cfd833dd102253ed2b04e7350b7938164e5259bada94ad2ad32` |

Actual local WSL checks using the frozen environment, Python3.14.8:

- Focused contract, public input and compatibility suite: **66 passed**.
- Complete offline suite: **640 passed, 37 integration cases deselected**, 21.64s.
  This duration is a run receipt, not an isolated performance comparison.
- Ruff lint/format: passed; architecture guard: passed; mypy: 36 inner/AI files passed.
- Repository skills validator: passed.
- Offline contract export: deterministic new schemas/manifest; existing public
  OpenAPI, v1/v2 analytics and SSE schema bytes unchanged.

Tests execute strict Pydantic contracts, exhaustive Portfolio route/region/locale
combinations, sensitive/unknown fields, cells/targets, and the current committed
wire examples. Canonical payloads are rejected by both current public input models.
Generated JSON schemas publish corresponding conditional requirements and forbid
unknown properties. An independent JSON Schema engine/client has not been exercised;
structural assertions do not establish cross-client validator compatibility.

No real service tests were rerun for this contract-only change. Existing PostgreSQL
analytics evidence remains separately attributed to its implementation revision.
No provider, LangSmith, geolocation, browser collector, Pequeverso runtime, Meta/CAPI
or production request was executed. Pequeverso must validate its own narrower
profile and authorization/consent behavior before implementing its new channel.

## Reusable fixture increment

Published synthetic fixtures, with unchanged runtime and schema bytes:

| Artifact | SHA256 |
| --- | --- |
| `analytics-semantics.examples.json` | `a058f6b21ebde843c2283d0e6b3f31796a38e341da461f804e24dd7b77ac2c50` |
| `product-analytics-v2.example.json` | `be55336b6a825d1d260aeb3cab65b0e4a85e3cb50038573fde4cd4d8fabd1789` |

The first file supplies eight calendar cases and fourteen country-boundary cases
to the existing tests, preserving their prior negative cases. The second wraps
one synthetic Portfolio private report in explicit fixture/scope metadata; only
its `report` field belongs to the private wire schema. The test validates it using
the actual strict response model and reconciles page/country/section and grid
totals, including suppressed clicks.

Focused period/country/core/profile/public-input/contract suite: **105 passed in
3.48s**. Ruff lint/format and local documentation links passed. The earlier 640-test
offline result above belongs to the earlier freeze increment; it is not a full
suite result for these added fixture cases. Current-head Actions must still pass.
No real-service, browser or production proof is added by these synthetic examples.
