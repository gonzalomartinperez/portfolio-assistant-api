# Aggregate analytics candidate — 2026-10-18

Application candidate on top of verified API develop
`dc6fdf357c2f21d87677bae1a3c02cea96aaa02d`. No public collector, Cloudflare account,
VPS deployment, paid model or real visitor data was enabled. Backoffice v2 rendering
and the website's committed-snapshot integration remain separate acceptance work.

Executed locally in WSL with the existing project-owned PostgreSQL 18.6/pgvector
0.8.7 image and disposable labelled fixtures:

- **607 offline tests passed**, 36 real-service tests deselected, 9.24 s.
- Strict mypy passed **36 inner-layer/AI source files**; this is not whole-API mypy.
- **Two real PostgreSQL tests passed**, 21.70 s: restricted-role/bootstrap permissions
  and real HTTP ingestion/report/recovery. The latter validates both input versions,
  duplicate replay, country/heatmap suppression, non-empty semantic actions,
  unauthorized/invalid reads, calendar-month end exclusion, 93-day retention,
  shared rate-limit rejection without incrementing totals, and logical restore with
  exact runtime grants reapplied. The restored aggregate fields/timestamps matched.
- Ruff checks passed. Skills/license checks passed; redacted known-pattern scanner
  reported no findings across 1,041 history blobs. This is not proof of absent secrets.

The country test uses an explicitly configured synthetic proxy peer/header; it does
not verify Cloudflare, geography accuracy or origin-bypass restrictions. No corpus,
Neo4j/provider, real OAuth or host website was needed for these analytics tests.
Private report body was below the existing 256 KB transport budget in the fixture;
this is not a maximum-traffic performance claim. No compiler/browser speedup is claimed.

Local logs: `artifacts/analytics-v2-offline-final.log`,
`artifacts/analytics-v2-restore-and-permissions.log`,
`artifacts/analytics-v2-secret-scan.json`. These are ignored diagnostics, not files
promised in a clean checkout. Reproduce with frozen API dependencies:

```sh
uv run pytest -q -m 'not integration'
TEST_INTEGRATION=1 PROJECT_POSTGRES_IMAGE=portfolio-assistant-postgres:project-proof \
  uv run pytest -q tests/test_interaction_integration.py tests/test_project_database.py
```

Build `project-proof` from this checkout's `Dockerfile.postgres` first. The fixture
runner refuses provider overrides, foreign images/containers and shared database URLs.
Review [contract/retention/edge requirements](../product-analytics.md#version-2-interaction-and-calendar-extension)
before consuming the new snapshot. Required Actions, paired UI/browser/accessibility
checks and actual deployment-chain acceptance must be reported separately.

## Independent review finding and regression

A bounded read-only peer found a real ordering race: transaction A could start
before B but acquire the global event lock after B. PostgreSQL `now()` is fixed
at transaction start, so an unconditional last-observed assignment could regress
freshness or violate the first/last constraint on initial collection. The upsert
now preserves `LEAST(first)` / `GREATEST(last)`. A controlled real-database test
holds the earlier transaction open, commits the later request first, then records
the earlier request and verifies both accepted events and exact timestamp extrema.

The report establishes its repeatable-read snapshot and derives its observation
clock/calendar window from PostgreSQL `clock_timestamp()`, aligning the report's
UTC clock with the stored receipt source. The focused HTTP/restore and reversed-order
suite passed **2 tests in 16.85 s** after the fix. Ruff and strict inner/AI mypy passed.
This is local regression evidence; required current-head Actions remain separate.
