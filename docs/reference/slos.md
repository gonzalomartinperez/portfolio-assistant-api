# Service level objectives

Status: defined 2026-11-22 (M6), not yet observed in production. The assistant is not deployed before MV
(DR-13), so every objective below is measured today only in CI and the load nightly; production burn-rate
alerts and dashboards are vps-ops task MV-2. Each objective uses a signal the API already exposes, so no new
instrumentation is needed on day one.

## Objectives

Windows are rolling 30 days, the same window `/internal/ops/v1/metrics` reports.

| Objective | Target | Service level indicator (SLI) and source | Error budget (30 days) |
|---|---|---|---|
| Readiness | 99.5% of one-minute probes succeed | `GET /readyz` returns 200 (schema, active corpus and graph checks), probed by the vps-ops monitor | 216 minutes not ready |
| Answer success | 99% of runs end in `run.completed` or a visitor `run.cancelled` | `assistant_executions_window{outcome}`: completed plus cancelled over all outcomes | 1% of runs end in `run.failed` |
| First fragment latency | p95 at most 1.5 s | `assistant_first_chunk_p95_seconds` (server time to the first answer fragment) | none: a breach is an incident |
| Stream health | at most 0.5% of streams fail or close before a terminal event | load nightly `error_rate`, `tests/load/budgets.json` | 0.5% of streams |
| Spend | never above the monthly cap | `assistant_usage_settled_usd` plus reserved, against `assistant_usage_budget_usd`; enforced atomically in code (DR-04) | none: requests are refused before the cap |

The latency and stream-health targets are the [load budgets](../decisions/024-load-budgets-baseline.md)
already enforced by `load-nightly.yml` on the stub app. With a real provider the first fragment includes model
latency, so that objective is re-baselined from the first live week (MV) and only ever tightened.

## What counts

- Requests refused for the visitor's own reasons (validation, ownership, rate limit) get a problem document
  before a run starts, so they never reach the answer-success SLI.
- A run that ends because the monthly budget is exhausted is the spend objective working, but the window gauge
  has no reason label yet, so today it counts against answer success. Splitting it out is part of MV-2.
- Planned maintenance windows announced by vps-ops are excluded from readiness.

## When the budget burns

1. Fast burn (2% of the monthly budget in one hour) pages the owner; slow burn (10% in three days) opens an
   issue. vps-ops owns the alert rules (MV-2).
2. While a budget is exhausted, only reliability fixes merge to `develop`; feature work waits.
3. Every page gets a short post-incident note in `docs/evidence/`.

## Correlation

Logs are JSON with `request_id`; when the trusted proxy sends `X-Request-ID`, the API reuses it, so one ID
follows a request through proxy and API logs ([API contract](api-contract.md)).
