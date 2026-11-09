# Audit: measured baseline of portfolio-assistant-api

Baseline: `origin/develop` at `e749ca762fb3f1e74225d9126d4eb1bbd88e2885` (2026-11-09), 394 tracked files, 331 commits. `main` is at `3da09ef`. Method: read-only export, `uv sync --frozen` (75 packages), fixture mode, no API key, no paid call. Evidence paths written as `audit/...` are in the planner's evidence bundle; the compact files are copied into this plan's [audit/](audit/) folder (the 868 KB Trivy report and the 511 KB coverage report are summarised in `audit/trivy-summary.json` and `audit/coverage-summary.json`). Label convention: **[measured]** command output, **[read]** code or docs read at the SHA above, **[hypothesis]** to be measured before acting.

## 1. Numbers table

| Metric | Value | Evidence |
|---|---|---|
| Source size | 8,673 lines in `app/` (95 files), 11,487 lines in `tests/` (58 test files plus support), 29 scripts, 9 migrations | [measured] `file-index.csv` |
| Tests | 866 collected: 819 offline pass in 31.7 s; 47 integration | [measured] `audit/pytest.txt`, `audit/pytest-integration.txt` |
| Integration run (audit environment) | **2 failed**, 45 passed in 108 s | [measured] `audit/pytest-integration.txt` |
| Coverage | **77.6% line, 68.7% branch** (3,575 statements, 956 branches, 143 partial); ecosystem floor is 85% branch | [measured] `audit/coverage-summary.json` |
| Coverage by layer (line / branch) | adapters 67.8 / 56.4; app entry points 19.1 / 21.4; bootstrap 84.6 / 71.7; domain 88.9 / 77.2; presentation 89.5 / 80.3; application 90.5 / 80.0; ai 91.3 / 75.0 | [measured] same |
| Lowest files | `knowledge_watch.py` 0%, `retention.py` 0%, `adapters/neo4j/projection.py` 8%, `adapters/postgres/retention.py` 12%, `postgres/conversations.py` 20%, `postgres/analytics_report.py` 21%, `postgres/analytics.py` 26%, `postgres/runs.py` 29%, `postgres/ledger.py` 32%, `application/conversations.py` 49% | [measured] same |
| mypy | Configured scope: 39 of 95 files (domain, application, ai, two adapters); config is `files = [...]` plus `strict = true`; scope passes (0 errors). **`mypy --strict app`: 199 errors in 38 of the 95 files** (142 `no-untyped-def`, 23 `no-untyped-call`, 7 `attr-defined`, 5 `assignment`, rest minor). By area: presentation 62, adapters/postgres 49, bootstrap 41, adapters/portfolio 24, providers 8 | [measured] `audit/mypy-config.txt`, `audit/mypy-strict-app.txt` |
| Sibling comparison | pequeverso-assistant-api: mypy strict clean on 123 files, coverage 85.0% line / 76.5% branch | [measured] `audit/pequeverso-assistant-api/` |
| Ruff | Repo ruleset: clean (288 files formatted). Ecosystem 10.2 families are not yet selected. With the sibling's ruleset: 1,349 findings, of which 1,085 `S101` (asserts; ignored in tests by the standard), 92 `PT018`, 37 `PT011`, 28 `S603`, 27 `S607`, 13 `B008`, 10 unused `noqa` | [measured] `audit/ruff-check.txt`, `audit/ruff-pequeverso-ruleset.txt` |
| Complexity (C901) | 11 functions above 10. Worst: `PublicRetrieval.search` **48**, `_sync` 28 (portfolio indexing), `safe_configuration` 26, `create_app` 21, `fixture_message` 21, `web_search.search` 19, `lifespan` 19, `answer.stream` 16, `runs._execute` 15, `graph.facts` 12, `lexical_score` 11 | [measured] `audit/c90-raw.txt` |
| Container image | **992 MB** (docker image size) versus **368 MB** for pequeverso-assistant-api; Trivy metadata layer size 669 MB versus 258 MB (different measure, same ratio of about 2.6x). Runtime stage installs `git` and four apt libs pinned by version | [measured] planner measurement, `audit/trivy-summary.json`; [read] `infra/docker/app/Dockerfile` |
| Image vulnerabilities | 60 HIGH (OS packages, 0 CRITICAL, 0 Python packages), **4 have a fixed version**; the repository gate is "fixable High or Critical" | [measured] `audit/trivy-summary.json` |
| BuildKit cache id | `--mount=type=cache,id=vps-ops-uv-python314`: copied from vps-ops, so two repos can share or poison one cache id on the same builder | [read] Dockerfile line 14 |
| Dependabot | `open-pull-requests-limit` 3 (uv), 2 (actions), 2 (docker), grouped by update type, so several PRs per week; violates the owner single-PR rule | [read] `.github/dependabot.yml` |
| CI | One workflow `quality.yml` (5 jobs plus aggregate `checks`), SHA-pinned actions, no path filters by design, two cross-repo checkouts (portfolio at a pinned SHA `1acbe54`, portfolio-backoffice at `5238643`), Postgres image built and migrated in both `database` and `container` jobs, Trivy binary downloaded with a checked SHA-256 (v0.75.0, newer than the 0.35.0 floor) | [read] |
| `pull_request_target` | `dependency-policy.yml` uses it (checks out `github.workflow_sha`, read-only token). Safe as written, but the ecosystem forbids the trigger class and zizmor will flag it | [read] |
| Supply chain | No CodeQL, no SBOM, no provenance attestation, no zizmor, no dependency-review, no Scorecard; in-house secret scanner exists; GitHub secret scanning and push protection state unverified here (v1 reported them off) | [read] workflows |
| Prompts | One inline f-string developer prompt of about 4.5 KB in `adapters/providers/answer.py`, concatenated with `voice_instructions()`; no version, no hash, not recorded in traces | [read] |
| Health endpoints | `/health/live`, `/health/ready` (ecosystem contract is `/healthz`, `/readyz`) | [read] `contracts/openapi.json` |
| Eval data | 1,000 cases in 100 families (670 development, 330 holdout; EN and ES halves), 40 adversarial, 15 multi-turn scenarios, 9 retrieval cases, historical live runs of 2026-10 (244 turns and smaller); **all 1,000 cases still `pending_real_answer_review`** | [measured] `evals/assistant.json`; [read] `docs/assistant-evaluation.md` |
| Holdout exposure | 200 of the 1,000 case IDs, **66 of the 330 holdout IDs**, appear in committed live or fixture result artifacts, exactly 2 IDs per family, so every one of the 33 holdout families has an exposed pair and 8 never-referenced variants (whether any ID reached a real model is not recoverable from the artifacts, so exposure is assumed) | [measured] ID scan over `evals/live-*.json`, `docs/verification/*.json` |
| Documentation | README 339 lines (target at most 250), 34 docs plus 46 dated verification records without hierarchy, ADRs 001-006 and 008 (007 missing), no CHANGELOG, no releases | [measured] |

## 2. Findings

Priority: **P0** blocks measurement or violates an owner rule now; **P1** blocks the 95 target; **P2** polish.

### P0

| ID | Finding | Evidence | Fix (plan reference) |
|---|---|---|---|
| P0-1 | **Golden retrieval data points at the portfolio's retired `src/content` layout.** `evals/retrieval.json` expects `src/content/{en,es}/*.ts`. Against the old layout hybrid passes 8/9. Against the portfolio's current layout (`content/{en,es}/*.ts`) hybrid passes **2/9**, vector 2/9, graph 3/9: the six answerable cases return the right files under the new path and fail only because the expected path is stale. The 2 that pass are the cases with no expected path. `tests/test_knowledge.py` consumes the same file. | `audit/eval-retrieval.json`, `audit/eval-retrieval-newlayout-develop.json`; `docs/coordination/portfolio-content-layout.md` | Layout-neutral gold evidence keys through `portfolio_paths` canonicalizer, rebuilt qrels, regression test that runs both layouts (PAA-D3, roadmap M1-1) |
| P0-2 | **A real retrieval failure hides behind it:** `unsupported-employer` (a no-answer case) returns evidence rows in both layouts, so the integration test `test_hybrid_retrieval_evaluation_and_relationship_provenance` failed in the audit run (corpus `b06c81e`, current layout). CI pins the older corpus `1acbe54`, where the last recorded runs were green, so whether the required check is red today is **unverified**; the frozen corpus snapshot removes the ambiguity. | `audit/pytest-integration.txt` | Becomes a golden abstention item; retrieval abstention threshold tuned under the ratchet (M2) |
| P0-3 | **Second integration failure:** `test_neo4j_effective_vendor_reporting_settings_are_disabled` failed in the audit run (effective Neo4j vendor-reporting settings differ from the expected `false`). CI starts Neo4j with `NEO4J_dbms_usage__report_enabled=false` and `NEO4J_server_bolt_telemetry_enabled=false`; the audit fixture most likely started it without them **[hypothesis]**. A failing required check caps the lens at 70, so M1 reproduces it in CI conditions first. | `audit/pytest-integration.txt` | Reproduce in CI image, fix fixture or assertion; keep the test (M1-3) |
| P0-4 | **Dependabot opens several PRs per week** (limits 3/2/2 with groups). Owner rule: exactly one. | `.github/dependabot.yml` | Rule rewrite plus guard (M1) |
| P0-5 | **BuildKit cache id copied from vps-ops** (`vps-ops-uv-python314`). | Dockerfile | Rename to `portfolio-assistant-api-uv-python314`, use registry cache per ecosystem 6.1 (M1) |
| P0-6 | **Holdout is not sealed:** 66 of 330 holdout IDs (2 per family, all 33 families) appear in committed result artifacts, while the docs present the split as a holdout. | measured above | Re-drawn sealed holdout from never-referenced variants, rephrased natively (PAA-D16, M2) |

### P1

| ID | Finding | Evidence | Fix |
|---|---|---|---|
| P1-1 | `mypy --strict app` has 199 errors; the configured strict scope covers 39 of 95 files, so the "strict typing" claim covers 41% of the app. | measured | Widen scope per package in M3, zero in M4; 142 are mechanical annotations suitable for a Codex worktree |
| P1-2 | `PublicRetrieval.search` complexity 48: hardcoded keyword boosts and TypeScript-syntax regexes, no per-rule ablation. | `app/ai/retrieval.py` | Declarative pipeline, RRF k=60, rule ablations (PAA-D18, M4) |
| P1-3 | The domain parses the portfolio's TypeScript format (`domain/fixture.py`, `domain/evidence.py` knowledge of `.ts`), contradicting "pure domain". | read | Move to `adapters/portfolio/source_format.py` (M4) |
| P1-4 | Coverage 77.6% line, 68.7% branch against an 85% branch floor; adapters 56.4% branch. Persistence and entry-point code (retention, watch, conversations, runs, ledger) is nearly untested offline. | measured | Integration-lane tests with real Postgres, entry-point smoke tests (M2) |
| P1-5 | No mutation, property-based, load, ZAP, Schemathesis or oasdiff testing. | read | testing.md |
| P1-6 | No golden set, no retrieval metrics beyond pass/fail, no validated judge, no cassettes. The only live evidence (244-turn run, 6-case smoke) is unreviewed. | read | assistant-quality.md |
| P1-7 | Prompt is inline, unversioned and unrecorded: a prompt change cannot be tied to a quality change. | read | PAA-D7, M2 |
| P1-8 | Image 992 MB, 2.7 times the sibling; `git` in the API runtime image although only the worker needs it; 4 fixable HIGH findings would fail the repo's own gate. | measured | api and worker targets (PAA-D11), measure `lingua` share first [hypothesis], M1 and M3 |
| P1-9 | CI duplicates Postgres build, migration and indexing in two jobs; no build-once; no SBOM or provenance; cross-repo checkouts make every PR depend on two other repositories being fetchable. | read | ci-cd.md; frozen corpus snapshot (PAA-D2) |
| P1-10 | No CodeQL, zizmor, Scorecard, dependency-review, release automation, CHANGELOG, immutable releases. | read | ci-cd.md |
| P1-11 | README 339 lines, caveat-first tone, no results table; docs without Diataxis; dated evidence mixed with living docs; ADR 0007 missing; `IMPLEMENTATION_STATUS.md` and `docs/work-checklist.md` hold volatile status prose. | measured | docs-and-community.md |
| P1-12 | Health endpoints and entry-point module names differ from the ecosystem deploy contract; changing them touches vps-ops. | read | PAA-D17, expand/contract |
| P1-13 | Skills: 5 skills (`api-verify-release` 191 lines, `api-maintain-knowledge` 103) with no activation evals; canonical directory is `.claude/skills`, the standard says `.agents/skills`. | read | skills.md (PAA-D13) |
| P1-14 | Eval isolation gap A1 from the 2026-10 audit (remote Neo4j accepted by the isolation guard) is still documented as open. | `docs/live-evaluation-readiness.md` | Close in `evals/harness/isolation.py` with rejection tests (M2) |

### P2

| ID | Finding | Fix |
|---|---|---|
| P2-1 | Sync DB access through `asyncio.to_thread` mixed with an async pool (v1 A5); loose entry points under `app/*.py` | Native async psycopg usage where it simplifies cancellation; entry points under bootstrap (M4) |
| P2-2 | No task runner, no pre-commit, no devcontainer; quickstart is 8 commands with port exports | `justfile`, `just demo` (M3) |
| P2-3 | `lingua` language detector footprint and cold start unmeasured [hypothesis] | Measure in the image spike; alternatives only if EN/ES parity holds on the golden language stratum |
| P2-4 | `ruff` ecosystem families not enabled (ANN, D, S, DTZ, ERA, TRY, ...) | Ratcheted per-file baseline, then zero (M3-M4) |
| P2-5 | In-house secret scanner duplicates gitleaks | Keep until parity shown, then retire |

## 3. Component and flow inventory

| Area | Contents (current) | Notes |
|---|---|---|
| Layers | `domain` (17 files), `application` (17), `ai` (3: workflow, retrieval, init), `adapters` (postgres 13, providers 7, portfolio 4, neo4j 3, observability 3, retrieval.py), `presentation` (12), `bootstrap` (8), five entry points under `app/` | Dependency rule enforced by `scripts/check_architecture.py` (AST) with negative probes in `tests/test_architecture.py`; domain and application are stdlib-only |
| Public API | 16 operations on 12 paths: session (3), conversations (4), messages list, stream, run read and cancel, feedback, suggestions, analytics event, two health | `contracts/openapi.json`, `contracts/sse.schema.json` |
| Private API | `/status`, `/metrics` behind an ops read token; operations and feedback overview schemas | `contracts/operations.schema.json` |
| Retrieval | Hybrid: pgvector semantic plus PostgreSQL text search (`simple` configuration) plus Neo4j relationship expansion; 5 sources reach the generator; fixture embeddings are 64-dimension hashes | `app/ai/retrieval.py`, `app/adapters/retrieval.py` |
| Generation | `ResponsesProvider` (OpenAI Responses API, model `gpt-6-luna`, medium effort, no fallback, no automatic billed retry) or `FixtureProvider`; optional bounded web context | `app/adapters/providers/answer.py` |
| Spend control | Atomic usage reservations, USD 10 monthly ceiling, per-reservation 0.05, configured prices 0.10 / 0.50 USD per million input / output tokens, embedding 0.02 | `app/domain/budget.py`, `app/bootstrap/config.py` (prices are repository configuration, not verified against the provider) |
| Tracing | `LANGSMITH_*` and `LANGCHAIN_TRACING*` are rejected by a settings validator; only private OTLP with scalar-only attributes | `app/bootstrap/config.py` |
| Knowledge sync | Worker reads the approved public portfolio repository by immutable commit, chunks Markdown by heading and TypeScript as `text_fallback`, projects to PostgreSQL and Neo4j, activates a version atomically | `docs/knowledge-sync.md` |
| Data | PostgreSQL 18 with pgvector (migrations 001-009), Neo4j 5.26 community | `migrations/`, `infra/` |
| Deploy | Image deployed by vps-ops (Coolify, VPS not purchased); this repo owns image, runtime contract, migrations | `docs/deployment-contract.md` |

## 4. Flows that matter for quality

1. Visitor question to answer: session cookie, bounded input, language resolution (lingua), retrieval (hybrid, 5 sources), prompt assembly, provider stream, citation validation, SSE events (closed set, 15 s heartbeat), usage accounting, persistence with 7-day retention.
2. Corpus update: worker poll (60 s) of the public portfolio, new immutable corpus version, projection, atomic activation. A layout change in the portfolio changes the corpus identity (`-v8` and `-semantic-v9` suffixes). This is why evals must not hard-code source paths.
3. Evaluation today: question bank to local loopback server to SSE sample report with raw answers, never graded for correctness.

## 5. What could not be measured (and why)

| Item | Blocked by | Stand-in |
|---|---|---|
| Real semantic retrieval quality | Fixture embeddings are hashes; real embeddings need a paid snapshot (estimated below USD 0.01 at the configured embedding price, **[hypothesis]**) | Lexical and graph lanes measured now; snapshot pre-authorized by DR-04 (PAA-D4) and taken in M2-16 (M2 day 1) |
| Real-model answer quality, TTFT, cost per answer | Paid calls | Fixture and cassette lanes; spend pre-authorized within DR-04 (caps in PAA-D9); P3 provisional 90 only until the owner spot check; floor 90 stated in the scorecard |
| Judge validity | Labels bootstrapped by agents (DR-05) plus a 20% owner spot check | Judge excluded from every gate until validated |
| Production observability, SLO burn, online evals, real load | VPS not purchased (Phase V) | Local stubbed-model load test; OTLP fixture receiver |
| GitHub settings (secret scanning, push protection, CodeQL, immutable releases) | Read needs repository admin API | First task in M1 records the live state in `docs/reference/repo-settings.md` |
| mutmut on Python 3.14 | Not run | Spike in M2 (PAA-D19) |
| Image size breakdown | Not run | Spike in M1 |
| Sealed holdout quality | Does not exist yet | Authored in M2 |
