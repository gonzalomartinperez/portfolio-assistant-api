# Research: testing strategy with targets

Planning research only. Baseline numbers come from the [baseline audit](audit-baseline.md).

## Target layout

```text
tests/
  unit/{domain,application,ai,presentation,adapters}/   # no I/O, < 30 s total
  integration/{postgres,neo4j,portfolio}/                # testcontainers or CI services
  contract/{openapi,sse,private}/                        # schemathesis, oasdiff, consumers
  e2e/                                                   # real image + proxy + SSE
  property/                                              # Hypothesis (or inside unit with a marker)
  security/                                              # authz/IDOR, CSRF, injection corpus
  eval/                                                  # deterministic regression suite
  load/                                                  # locustfile.py (does not run in pytest)
```

Markers: `unit`, `integration`, `contract`, `e2e`, `property`, `security`, `eval`,
`slow`.

## By type

| Type | Tool | Scope | Target |
|---|---|---|---|
| Unit | pytest + pytest-xdist | domain/application/ai/presentation | < 30 s; branch coverage per layer (below) |
| Integration | CI services today; `testcontainers` (pinned digests) locally | migrations, ledger, conversations, retention, graph projection, index | every table/query in `adapters/postgres` and `neo4j` with at least one real test |
| Contract (provider) | `schemathesis` over `contracts/openapi.json` against the fixture app; validation of every SSE event with `jsonschema` | `/api/v1/**` | 0 failures in a 500-example fuzz per endpoint; responses valid against the schema |
| Contract (consumers) | `oasdiff breaking` + JSON Schema diff on PRs; publish contracts as a versioned asset; a cross job that compiles the generated types of the pinned portfolio/backoffice | portfolio (public), backoffice (private: operations, analytics, feedback; byte comparison today) | breaking change ⇒ failure unless labelled `contract-major` + ADR |
| E2E | real image + `scripts/container_smoke.py`/`proxy_smoke.py` (exist) + full flow session→stream→history→delete | image | exists; add SSE with `httpx-sse` and mid-stream cancellation |
| Property-based | Hypothesis | `domain/budget` (Decimal invariants: reserve ≥ settle, never exceeds the cap), `evidence`/citation mapping, `analytics_periods`, `privacy` redaction, monotonic SSE sequence; **stateful** for the run lifecycle (`RuleBasedStateMachine`: started→delta*→completed/failed/cancelled, never two terminals) | ≥ 12 properties; CI profile 200 examples, nightly 2,000 |
| Mutation | **mutmut 3.x** (v3.5.0, Feb-2026; requires fork → WSL/Linux; does not mutate code outside functions) | all of `domain/`, all of `application/`, `ai/retrieval/fusion.py` and `selection.py` | score: domain ≥ 85%, application ≥ 75%, ai ≥ 70%; nightly ≤ 30 min with parallelism; PR: changed modules only, informational |
| Load | **Locust** (Python, same language; own SSE client measuring TTFT, gap between deltas, terminal); k6 has no native SSE | fixture provider with simulated latency; real Postgres/Neo4j | 20 concurrent streams sustained for 10 min on 2 vCPU: p95 overhead ≤ 150 ms, 0 leaked connections, stable RSS (±10%) |
| Security | ruff `S`, CodeQL, authz tests (another session id ⇒ 404), CSRF, size limits, injection corpus, promptfoo subset | API | 0 high in CodeQL; 100% of endpoints with an ownership test |

## Coverage targets (combined unit + integration, branch)

| Layer | Today (unit, statements) | Branch target |
|---|---|---|
| domain | 89% | ≥ 98% |
| application | 91% | ≥ 95% |
| ai | 91% | ≥ 92% |
| presentation | 89% | ≥ 92% |
| adapters | 68% (unit) | ≥ 88% (combined) |
| bootstrap | 85% | ≥ 80% |
| total | 80% | ≥ 92%, CI gate + `diff-cover` ≥ 95% on new lines |

Use `COVERAGE_CORE=sysmon` (coverage.py over `sys.monitoring`, Python 3.12+) to reduce
overhead.
