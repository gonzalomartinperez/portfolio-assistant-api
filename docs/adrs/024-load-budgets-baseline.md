# ADR024: Load budgets and baseline ratchet

Status: accepted (2026-11-14, master plan task M2-13).

## Context and problem

The scorecard axis D6 has no enforced latency, error or memory budget and no load
test. `docs/master-plan/testing.md` section 3 sets the targets. The numbers cannot be
measured on a developer host (3 CPUs, heavily loaded), so the first trustworthy
numbers come from the nightly runner.

## Considered options

1. Enforce the testing.md budgets from day one and fail the nightly on any miss.
2. Run the nightly report-only until a baseline exists.
3. Enforce the budgets, and let a recorded baseline relax a metric until it is tightened.

## Decision

Option 3. `tests/load/budgets.json` holds the budgets and an initially empty
`baseline` map. The nightly (`load-nightly.yml`, Locust with an httpx SSE client over the
stubbed-provider app, 30 users for 15 minutes) fails when a measured metric exceeds its
limit, where the limit is the baseline value if one is recorded, else the budget.

| Metric | Budget |
| --- | --- |
| Time to first event p95 | 1500 ms |
| Inter-event gap p95 | 500 ms |
| Error plus premature close rate | 0.5% |
| Concurrent streams | 30 (3 times the expected 10) |
| RSS growth over the 15-minute soak | 20% |

Ratchet rule: the first nightly run on the CI runner sets the baseline only for a metric
that misses its budget, by a PR that edits `baseline` and links the report artifact. A
baseline may only be lowered toward the budget, never raised, and is removed once the
metric meets the budget; raising it needs a new ADR and the owner. A 20-second smoke
profile is for local verification and does not check RSS growth.

## Consequences

- The load run exercises routers, middleware and workflow, not PostgreSQL, Neo4j or a
  provider; it bounds API overhead, not end-to-end latency.
- The local smoke run (5 users, 20 s) met every budget; the soak numbers are unverified
  until the first nightly.

## Confirmation

`tests/load/test_budgets.py` covers the budget comparison, the minimum completed streams, missing samples and that `budgets.json` defines exactly the four budgets with baseline keys among them; the lower-only rule for baselines is enforced in review;
`load-nightly.yml` uploads `load-report.json` each night.

The nightly adds `ZPL-2.1` to the dependency-review allowlist: locust pulls in `zope.event` and `zope.interface` (ZPL-2.1, permissive and OSI-approved) in the `load` group only, which is not shipped in the image.
