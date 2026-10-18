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
