# Testing plan

Applies ecosystem section 11 (catalog 11.0, thresholds 11.1, tooling 11.2, cadence 11.3) to an assistant API. Research: [04](research/04-testing.md) and [03](research/03-rag-evals.md). Baseline numbers are in [audit.md](audit.md): 866 tests (819 offline in 31.7 s, 47 integration in 108 s with 2 failing), coverage 77.6% line and 68.7% branch, adapters 56.4% branch, no mutation, property, load, DAST, Schemathesis or oasdiff.

## 1. Lane layout (replaces 58 flat files)

| Lane | Directory | Needs | Marker | Runs |
|---|---|---|---|---|
| Unit | `tests/unit/` | nothing | none | every PR |
| Property | `tests/property/` | nothing | `property` | PR (profile `ci`), nightly (profile `nightly`) |
| Architecture | `tests/architecture/` | nothing | none | every PR |
| Contract | `tests/contract/` | nothing, plus oasdiff binary | `contract` | PR when `contracts/**` or API code changes, nightly |
| Evals and graders | `tests/evals/` | nothing (recorded provider) | none | PR (assistant-quality profile and graders) |
| Tooling and harness | `tests/tooling/`, `tests/harness/` | nothing | none | every PR |
| Integration | `tests/integration/` | PostgreSQL 18 with pgvector and Neo4j 5.26 in containers | `integration` | every PR (sharded when over budget) |
| SSE and HTTP end to end | `tests/e2e/` | running app in the built image, stubbed provider | `e2e` | PR smoke, nightly full |
| Load | `tests/load/` (Locust) | built image | none | nightly and release |
| Container | `tests/container/` + `container-structure-test.yaml` | built image | `container` | every PR that touches Docker or runtime, release |

Rules: random order (`pytest-randomly`), no shared mutable state between tests, session-scoped containers with per-test cleanup (Neo4j `DETACH DELETE`, PostgreSQL rollback or truncate), integration lane under 90 s (today 108 s: fix by indexing the frozen corpus once per session and starting both databases in parallel), no live model call in any default lane, `pytest.mark.integration` tests never skip silently in CI (the job fails if collected count is below the committed floor).

## 2. Thresholds and ratchets

| Item | Baseline | Gate and path |
|---|---|---|
| Static | ruff clean on a small ruleset; mypy 199 errors on full app | ecosystem ruff families and `mypy --strict` over all of `src/`: 0 (ratchet counts in `scorecard/ratchets/static.json`; M3 widens scope per package, M4 reaches 0) |
| Branch coverage (whole repo) | 68.7% | Ratchet starts at the measured value; exit floors: M2 at least 80%, M3 at least 85% (ecosystem floor); per layer: domain and application at least 90%, adapters at least 80% (via real services), entry points at least 75% |
| Line coverage | 77.6% | informational; floor 90% by M4 |
| Diff coverage on PR | none | at least 90% (`diff-cover` on `coverage.xml`), effective from M2 |
| Mutation | none | mutmut 3 (forkserver), scope in section 3; PR incremental on changed files, weekly full; break 60, target 75; graders and budget math target 85 |
| Mix by lane (share of test count) | unit about 95%, integration about 5% | ecosystem asks 20/60/at most 5/rest; **deviation T1**: by M6 integration at least 45% of the count (the evals and domain layers hold many cheap pure tests that stay unit); ratchet in `tests.json`; revisit at M6 |
| Flaky tests in required checks over 30 days | unmeasured | 0 (ecosystem 6.3); nightly flake detector runs unit lane 3 times and integration lane 2 times with random seeds; quarantine cap 2% or 5 |
| Integration suite time | 108 s | under 90 s |
| Offline suite time | 31.7 s | under 60 s with `pytest-xdist` if it grows |

## 3. Mapping of every row of ecosystem 11.0

| Family | Types in this repo | Tool | Scope and threshold | Cadence |
|---|---|---|---|---|
| Correctness | Unit | pytest | `tests/unit/`; branch floors section 2 | PR |
| | Integration with real databases | pytest, containers (compose services in CI, `infra/compose/local.yaml` locally), optional Testcontainers later | PostgreSQL 18 plus pgvector and Neo4j 5.26; frozen corpus indexed once; migrations 001-009; under 90 s | PR |
| | Component (all states) | not applicable | no UI; response states (loading, error, partial) are covered by SSE tests | n/a |
| | Architecture and boundary | import-linter (`layers`, `forbidden` third-party in domain and application, `independence` between adapters) plus `scripts/check_architecture.py` for call-level rules, with negative fixtures | 0 violations, empty baseline | PR |
| Test quality | Mutation | mutmut 3 (spike on Python 3.14 first, PAA-D19; fallbacks `mewt`/`muton` via the mutation-testing skill) | `domain/` (budget, privacy, evidence, analytics periods, web policy), `application/` (answer, runs, conversations, contracts), `ai/retrieval/{fusion,rules}`, prompt loader, `evals/harness/graders`; break 60, target 75, graders 85 | PR incremental (changed files, budget 30 min), weekly full (90 min) |
| | Branch and diff coverage | coverage.py (branch mode), `diff-cover` | section 2 | PR |
| | Flake detection | `pytest-randomly`, repeated nightly runs | 0 flaky over 30 days | nightly |
| Input space | Property-based | Hypothesis, profiles `ci` (100 examples) and `nightly` (1,000) | budget math (reservation never exceeds ceiling, release is idempotent), privacy minimization (idempotent, never longer, never leaks patterns), `portfolio_paths.canonical_key` (layout neutral, round trip, both layouts equal), RRF fusion (permutation of candidates does not change the set, monotone in rank), citation mapping, SSE framing (closed event set, exactly one terminal), analytics period boundaries in America/Argentina/Buenos_Aires, language policy, chunker invariants (offsets cover the text once), idempotent ingestion; one stateful machine for session and conversation lifecycle (50 steps) | PR (ci), nightly |
| | API fuzzing | Schemathesis from `contracts/openapi.json`, explicit OpenAPI links for 5 stateful flows (session to conversation to stream to run to feedback, cancel, delete) | 50 examples per operation on PR, 500 nightly; negative cases on auth and validation | PR short, nightly long |
| | Parser and validator fuzzing | Hypothesis on knowledge manifest and projection validators, `scan_secrets` patterns | no crash, deterministic rejection | nightly |
| Contracts | Breaking-change detection | oasdiff `breaking` vs the base branch, JSON Schema diff for `sse.schema.json` and event schemas | 0 breaking without the `contract-major` label | PR (profile `contract`) |
| | Schema and example validity | pytest with `jsonschema` | every example in `contracts/*.examples.json` validates; every response model matches the snapshot (`contracts.export` drift check kept) | PR |
| | SSE conformance | pytest over the ASGI app and over the container | frames, `event` names from the closed set, heartbeat every 15 s, one terminal event, reconnect through `GET /runs/{id}` (no `Last-Event-ID` resume is defined in v1: stated as not applicable), disconnect cancels the provider call and releases the reservation | PR |
| | Cross-repo consumers | cross job compiling the portfolio site and backoffice generated types against the snapshot (ecosystem 18.1) | green or the PR is labelled `contract-major` | PR (contract profile), nightly |
| | Product event schemas | JSON Schema diff both sides | closed event set; default-off analytics | PR |
| End to end | User journeys | pytest plus httpx against the running image with the fixture provider | session, conversation, stream, cancel, feedback, delete; 6 journeys | PR smoke, nightly |
| | Checkout hand-off | not applicable | no checkout here | n/a |
| | Auth journeys | pytest | session cookie lifecycle, ops token on private routes, exact-origin CSRF | PR |
| | Cross-browser, real device | not applicable | API only; browser behaviour is tested in the site and backoffice repos | n/a |
| Visual | Screenshots | not applicable | no UI | n/a |
| Accessibility | axe, keyboard, zoom | not applicable | no UI. API-side equivalent is error and message clarity, covered by P1 and P3 checks | n/a |
| Performance | Latency p95, TTFT | `pytest-benchmark` for retrieval and fusion, Locust timings, eval-report budgets | section 11 of [assistant-quality.md](assistant-quality.md) | PR (benchmarks and budgets), nightly |
| | Bundle, Lighthouse, RUM | not applicable | no frontend; image size is the analogue (ratchet) | n/a |
| Load and resilience | Load, stress, soak | Locust with an httpx streaming client, stubbed provider | time to first event p95 under 1.5 s, inter-event gap p95 under 500 ms, error and premature close under 0.5%, 3 times the expected peak concurrent streams (assume 10 expected, so 30), RSS growth under 20% over 15 minutes, 15-minute soak | nightly, release |
| | Dependency-failure tests | pytest with fault injection (stop container, firewall, slow provider) | PostgreSQL down, Neo4j down, provider timeout, provider error, budget exhausted, rate limit, knowledge updating: each yields the documented problem code and no 500, graph failure degrades to vector and lexical | PR (fast subset), nightly |
| Security | SAST | CodeQL (python and actions) | 0 open high | PR (default setup), weekly |
| | Secrets | gitleaks plus GitHub secret scanning and push protection; in-house `scan_secrets.py` until parity | 0 findings; secret-serialization audit (`repr`, `model_dump`, logs, spans) as a unit test | PR |
| | Dependency and licence review | dependency-review action, `check_license` | no new High or disallowed licence | PR |
| | Container scan | Grype on the built digest | 0 fixable High or Critical (4 today) | PR, release |
| | DAST baseline | OWASP ZAP API scan against the running image using the OpenAPI file | 0 medium or higher | nightly |
| | Authorization matrix | pytest | a test enumerates every registered route and fails if a mutating route is missing from the matrix (session ownership, wrong owner returns 404 consistently, ops token, unauthenticated 401, exact origin, rate limit); object-ID swap for conversations, runs, messages | PR |
| | CSRF and Origin, session expiry | pytest | every mutating route; expiry and revocation | PR |
| | Headers | pytest | security headers on all responses; no stack traces | PR |
| | RSC and DTO leaks | not applicable | no RSC; response models are explicit and snapshot-tested | n/a |
| | Prompt injection and red team | in-repo attack pack (60) plus weekly sweep | [assistant-quality.md](assistant-quality.md) section 9 | PR (pack), weekly (sweep, spend-capped) |
| AI quality | Golden set, deterministic graders, retrieval metrics, judge validation, prompt-version regression | pytest graders, ranx, cassettes | [assistant-quality.md](assistant-quality.md) | PR (profile assistant-quality), release (live) |
| Data | Migrations | pytest on PostgreSQL containers | upgrade from empty; upgrade from N-1 schema; checksum and order immutability of 001-009; forward-only (no down); new migrations are expand-first | PR |
| | Idempotency, grants | pytest | rerunning migrations and indexing is a no-op; `deploy/runtime-grants.sql` allows chat and cleanup and denies corpus writes and schema creation | PR |
| | Seed and fixture safety | pytest | fixtures contain only approved public content; isolation guard rejects remote targets (both databases) | PR |
| | Backup restore drill | `pg_dump` and restore round-trip test in a container (drill-lite); the real monthly PITR drill belongs to vps-ops | round trip equality of corpus and ledger tables | nightly (lite); monthly (vps-ops, Phase V) |
| Build and runtime | Container structure | container-structure-test | non-root 65532, no shell tools beyond need, no `pip`, labels per ecosystem 8.4, no `git` in the api target, entry points | PR (Docker changes), release |
| | Image smoke | `scripts/container_smoke.py` (streaming and SIGTERM), `proxy_smoke.py`, read-only root with tmpfs `/tmp` | health, readiness, graceful shutdown under 25 s, reservation released | PR (Docker changes), release |
| | Hosting contract, post-deploy | `/readyz` returns `version` equal to the release SHA | Phase V (vps-ops) | MV |
| Infrastructure | Host baseline, Ansible, drift | not applicable | owned by vps-ops; here `validate_compose.py` keeps validating compose hardening | n/a (compose check PR) |
| Content and SEO | Copy invariants | unit | fixed strings (errors, starters, fixture answers) never state invented facts; owner name written exactly "Gonzalo Martin Perez" | PR |
| | Spanish locale checks | in-repo unit test with a regex lint for voseo and regionalisms over static Spanish strings (no Node tool added to a Python repo) | static Spanish strings use neutral Latin American Spanish | PR |
| | Structured data, metadata, sitemap | not applicable | API | n/a |
| | Link check | lychee | docs | PR (docs profile), weekly |
| Time and concurrency | Frozen time and timezone | `time-machine` | analytics calendar periods, retention, rate windows in America/Argentina/Buenos_Aires; introduce a `Clock` port so `datetime.now()` is not called outside it (today it is called in prompt assembly) | PR |
| | Races | pytest-asyncio with concurrent tasks against real PostgreSQL | atomic budget reservations never exceed the ceiling under 50 concurrent reservers; run lease takeover; concurrent cancel and completion produce one terminal | PR |
| Observability | Log redaction | unit plus integration | no visitor text, tokens, cookies, DSNs in logs or spans; structured JSON with request id | PR |
| | Metrics endpoint contract, request id | integration | `/metrics` and `/status` schema; `x-request-id` propagated into logs; OTLP payload test against a fixture receiver (exists) | PR |
| Harness | Skill activation evals | check scripts per ecosystem 15.1 | trigger accuracy drop under 10 points | PR (skills changed), monthly |
| | Docs checks | markdownlint-cli2, lychee, README heading check, AGENTS command test | 0 | PR (docs profile) |
| | Standards drift, CI profile coverage | `tests/harness/test_ci_profile.py` | every tracked file matches at least one profile in `ci-profile.json`; standards.lock hashes match | PR, weekly |
| Production synthetics | Uptime and read-only probes | Uptime Kuma on `/readyz` and the suggestions endpoint (no model call), scheduled smoke | Phase V (vps-ops) | MV |

## 4. Eval lanes in the test plan

The eval harness is tested like production code: graders have unit tests and mutation targets; the distillation tool is run once and its output is frozen with a manifest test (counts per stratum and locale, schema validity, no duplicate normalized questions, golden items present in full set or archived with reason); the cassette recorder has a replay test; the isolation guard has rejection tests for each database. The golden lane is a pytest module (`tests/evals/test_golden.py`) so that `pytest -m "not integration and not e2e"` can run it and its failure output lists failing item IDs by stratum.

## 5. Flake and quarantine

Policy is ecosystem 6.3 without exceptions: no blanket retries on unit tests; a test that fails once on `main` opens a `flaky` issue and is quarantined the same day (listed in `tests/quarantine.toml`, run in a non-blocking job); fix or delete within 7 days; first-attempt failure rate on `main` over 2% across 20 runs stops feature work. The 2 integration failures at the audit SHA are not quarantined: they are P0 findings closed in M1.

## 6. Known risks

| Risk | Mitigation |
|---|---|
| mutmut 3 on Python 3.14 untested | Spike in M2 (half day); fallback tools through the mutation-testing skill; scope reduced rather than score loosened |
| Real-service tests slow the PR path | Session-scoped containers, frozen corpus indexed once, shard when over 5 min p50 |
| Cassettes become stale after every retrieval tweak | Incremental re-record under the cap; retrieval is gated by its own metrics lane that needs no cassette |
| Hypothesis stateful tests are flaky by construction | Fixed seeds in PR (derandomized profile), random seeds nightly only |
