# Target state

Pragmatic Clean Architecture for an assistant API (ecosystem section 9 and 10.2). What exists and works is kept; layers that would only forward calls are not added (owner decision O3). Research: [02](research/02-python-architecture.md), [10](research/10-standards-dependencies.md). Baseline: [audit.md](audit.md).

## 1. What is kept (do not touch)

| Kept | Why |
|---|---|
| Six layers: `domain`, `application`, `ai`, `adapters`, `presentation`, `bootstrap`; the dependency rule | It is already enforced by an AST guard with negative probes and an empty baseline; renaming `presentation` to `api` or `ai` to `workflow` buys nothing and costs a 394-file churn. The deviation from the ecosystem names is PAA-D21 in the README (names kept, ports under `application/ports/`) |
| `Protocol` ports, no DI framework, composition root in `bootstrap` (lifespan) | Matches ecosystem 9 ("no DI framework"); 32 `Protocol` references today |
| Domain and application stdlib-only | Strongest property of the codebase; mutation and property tests target exactly these layers |
| Atomic spend reservations, run leases, cancellation semantics, SSE closed event set, session ownership, exact-origin CSRF | They are the product's safety invariants and are covered by tests that stay |
| Public v1 wire contract | Only additive changes (section 6) |
| Fixture mode as default, `ALLOW_PAID_AI=false`, tracing refused by the settings validator | Privacy and spend guarantees (invariant 3 and the owner's spend rule) |
| Migrations 001-009 immutable | Forward-only history; checksum test |

## 2. Target layout (after M4)

```
src/portfolio_assistant/
  domain/            pure policy: budget, privacy, evidence scoring, graph facts, analytics periods, errors, portfolio_paths (canonical keys), clock value types
  application/
    ports/           Protocols: Provider, Embeddings, SemanticSearch, LexicalSearch, GraphExpansion, Ledger, Conversations, Runs, Clock, WebSearch, ...
    (use cases)      answer, runs, conversations, feedback, analytics, knowledge, knowledge_watch, evaluation_export, ...
  ai/
    workflow.py      LangGraph graph with injected capabilities
    retrieval/       pipeline.py, candidates.py, fusion.py, rules.py, rules.toml, select.py   (replaces the 399-line retrieval.py, search() CC 48)
  adapters/
    postgres/  neo4j/  providers/ (answer.py, fixture_answer.py, embedding.py, language.py, voice.py, web_search.py, http.py)
    portfolio/ (indexing.py, projection.py, watch.py, source_format.py: the only place that knows the portfolio TypeScript format)
    observability/  retrieval.py (candidate adapter)
  presentation/      HTTP and SSE, request and response models, problem documents, middleware
  prompts/           answer.md, voice.en.md, voice.es.md, web-context.md, prompts.lock   (package data, loaded by ai/prompts.py)
  bootstrap/         config.py (settings), container.py (composition root), logging.py, entrypoints/ {api, migrate, retention, knowledge_sync, knowledge_watch}.py
contracts/           openapi.json, sse.schema.json, schemas, examples, export.py   (unchanged location)
evals/               golden/, full/, calibration/, retrieval/, attacks/, cassettes/, baselines/, corpus/, schema/, archive/, harness/   (not shipped)
scorecard/           aggregator and ratchets
scripts/             repository tooling kept (check_architecture.py, check_license.py, container_smoke.py, ...)
tests/               unit/ property/ architecture/ contract/ evals/ harness/ tooling/ integration/ e2e/ load/ container/
migrations/ deploy/ infra/ docs/
```

Source files that stay under `app/`-relative names keep them (`app/domain/budget.py` becomes `src/portfolio_assistant/domain/budget.py`); every file's destination, split or deletion is in [file-index.csv](file-index.csv). There are no `.js`, `.mjs` or `.cjs` files in the repository.

## 3. Guards

| Guard | Rules | Negative fixtures |
|---|---|---|
| import-linter (`[tool.importlinter]`) | `layers`: `bootstrap` over `presentation | adapters | ai` over `application` over `domain` (siblings independent: this encodes today's ALLOWED table, where adapters may not import `ai` or `presentation` and vice versa); `forbidden`:`domain` and `application` may not import `fastapi`,`starlette`,`psycopg`,`neo4j`,`openai`,`langgraph`,`langchain_core`,`pydantic`,`uvicorn`;`independence`:`adapters.postgres`,`adapters.neo4j`,`adapters.providers`,`adapters.portfolio`,`adapters.observability` | `tests/architecture/test_import_linter_probes.py` writes a temporary illegal import for each contract in a temp package and asserts a failure |
| `scripts/check_architecture.py` (kept, reduced) | Only what import-linter cannot say: domain and application stdlib-only (including dynamic `importlib` and `__import__`), banned calls (`datetime.now`, `datetime.utcnow`, `time.time` outside the `Clock` adapter, `os.environ` and `os.getenv` outside `bootstrap/config.py`, `print`, `subprocess` outside adapters and bootstrap), no `app.` imports in `src/`, entry points only under `bootstrap/entrypoints/` | existing probes kept and extended |
| Dead code | `vulture` over `src/` with a committed allowlist that only shrinks | a planted unused function must be reported |
| Complexity | ruff `C901` with `max-complexity = 10`, per-file baseline in `scorecard/ratchets/static.json` that only decreases (11 functions above 10 today, max 48) | n/a |
| Typing | `mypy --strict` on `src/`, `evals/`, `scorecard/`, `scripts/`; tests with `disallow_untyped_defs = false` only | n/a |
| Contracts | `contracts.export` drift check plus oasdiff | a planted breaking edit must fail |

All guards run in pre-commit, `just check` and CI (one command equals the CI static job, ecosystem 10.3).

## 4. Typing and lint policy

| Topic | Policy |
|---|---|
| Python | `requires-python >=3.14,<3.15`, `src/` layout, uv with `exclude-newer = "7 days"` and `uv sync --locked` |
| Ruff | Explicit families `E W F I B C4 UP SIM RUF PERF PIE PT PTH TC ASYNC S T20 TRY ARG FAST LOG G DTZ ERA FURB N RET D ANN`, ignore `E501 TRY003 D203 D213`; tests ignore `S101 ANN D ARG`; line length 100, double quotes (the repo uses single quotes and 88 columns today: one `ruff format` mechanical PR, deviation removed) |
| Docstrings | Google convention on public contracts and operationally sensitive methods (kept from CONTRIBUTING) |
| mypy | Strict over all of `src/`. The 199 current errors by area are the work queue: presentation 62, adapters/postgres 49, bootstrap 41, adapters/portfolio 24, providers 8, observability 5, `adapters/` root 5, neo4j 2, entry points 3. By rule: 142 `no-untyped-def` (mechanical annotations), 23 `no-untyped-call`, 7 `attr-defined`, 5 `assignment`, 4 `func-returns-value`, 4 `arg-type`, 3 `type-arg`, 3 `call-overload`. Rule: no `Any` and no `# type: ignore` to silence adapter SDKs; translate SDK-shaped values to typed contracts at the adapter (existing CONTRIBUTING rule). The scope widens package by package (M3: adapters/providers, observability, neo4j, portfolio; M4: postgres, bootstrap, presentation) and the file list in `[tool.mypy]` disappears when the scope is `src/` |
| Second checker | Pyrefly or pyright strict as a non-blocking job (ecosystem 10.2); `ty` editor only |
| Settings | Frozen `BaseSettings`, secrets as `SecretStr` (today `Field(repr=False)` strings), built once in the lifespan. **Deviation**: `extra="forbid"` is not usable with a dotenv source (it would reject unrelated entries), so unknown or missing keys are caught by a test that compares `Settings`, `.env.example` and the published env schema, and `extra="ignore"` stays |
| Time | A `Clock` port; the prompt's "current date" and analytics use it; guard bans direct `datetime.now()` |
| Errors and logs | RFC 9457 problem documents (section 6); structured JSON logs with request id; no visitor text, tokens or DSNs |
| Async | psycopg async pool through one adapter module; remove `asyncio.to_thread` mixing where it complicates cancellation; keep sync only for one-shot CLI paths (v1 A5, P2-1) |

## 5. Retrieval and domain refactor (PAA-D18)

| Change | Rule |
|---|---|
| `ai/retrieval.py` (399 lines, `search` CC 48) to a pipeline | Stages as small functions: candidates (semantic, lexical, graph via ports) then `fusion` (reciprocal rank fusion, k = 60 default, parameter in config) then declarative `rules.toml` boosts (each rule has an id, match, weight and locale, and can be disabled by id for ablation) then `select` (at most 5 sources and 19,000 characters, existing bound). Every function CC at most 10 |
| Acceptance | Golden 100% and the retrieval ratchet unchanged (no significant drop, Recall@5 within the first baseline); per-rule ablation table committed in `docs/explanation/retrieval.md`; rules without measurable contribution are deleted |
| Portfolio format out of the domain | `domain/fixture.py` and the TypeScript-aware parts of `domain/evidence.py` split: format parsing to `adapters/portfolio/source_format.py`; fixture answer text to `adapters/providers/fixture_answer.py`; the domain keeps scoring and policy only |
| Layout neutrality | `domain/portfolio_paths.canonical_key()` is the only path-to-key mapping; all stored citations keep the physical path (existing guarantee) |
| Per-language text search | If H1 shows a gain, additive migration 010 adds generated `tsvector` columns per language (`english`, `spanish` plus `unaccent`); old column kept for one release |
| Evidence sufficiency | The retrieval result carries `evidence_sufficient` so abstention is not decided by the prompt alone (P0-2); threshold set by ablation |
| Run metadata | Additive migration 011 (only if needed for reports) stores `prompt_version` and `model_snapshot` on runs; otherwise they stay in telemetry attributes only. Expand only |

## 6. Public contract v1.1 (additive, PAA-D17)

Rule (ecosystem 3.3): expand first, consumers refresh, contract later, removal is a major with ADR and `contract-major` label. Nothing below removes or changes a v1 field.

| Change | Detail | Consumer impact |
|---|---|---|
| Problem documents | Error bodies become RFC 9457 `application/problem+json` with `type`, `title`, `status`, `detail`, and extension members `code` (closed enum), `retryable`, `retry_after_s`, `messages` (`en`, `es`) | Consumers ignore unknown members; the site shows `messages[locale]` when present |
| SSE progress | Additional event `run.progress` with `phase` in `retrieving`, `reading`, `writing`, sent only when the request opts in (`X-Assistant-Progress: 1`), so strict v1 consumers see no new event | Cross job proves the current site and backoffice code tolerate the event before it is enabled by default |
| Health | `/healthz` and `/readyz` added next to `/health/live` and `/health/ready` (section 7 of ci-cd.md) | vps-ops lock PR |
| Starter suggestions | Unchanged | none |
| Examples | Every example validated against its schema in tests | none |

### 6.1 Assistant experience v2 additions (additive v1.x, PAA-M4-X and PAA-M5-X; detail in [assistant-experience.md](assistant-experience.md))

All additions are opt-in or flag-gated, default off, and remove nothing from v1 (expand first, dual-write for one release).

| Change | Detail | Gate and ADR |
|---|---|---|
| Rich `blocks` | Closed union of block types with closed `icon_id` enums and URL allowlist, requested by header; legacy fields dual-written | Block JSON Schema, executable examples, oasdiff additive; ADR 0024 (M5) |
| `capabilities` | Server reports which optional features are on (`blocks_v2`, `progress_events`, `memory`, `web_access`) so consumers feature-detect | Contract tests; same ADR 0024 |
| Memory endpoints | `GET /v1/memory`, confirm, and `DELETE /v1/memory`; opt-in, closed schema, propose-then-confirm, 60-day fixed TTL, retention job, `MemoryStore` port with in-memory and Postgres Store adapters | Isolation, forget and canary property tests; ADR 0025 (M5) |
| Semantic and retrieval cache | Embedding cache, retrieval-id cache and starter replay only; never a free-form answer cache (AX-D7); `RetrievalCache` port, kill switch flag `semantic_cache` | Eval threshold, overhead p95 <= 150 ms; ADR 0026 (M4) |
| Web access | `WebSearch` port, fixed query per topic, snapshot ingestion primary, hosted search for currentness only, host allowlist, sanitization, flags `web_access` and `web_official_help` | Tool-use evals 100%, injection fixtures, caps tested; ADR 0027 (M4) |
| Runtime flags | DB-backed `Flags` port, audited, effective without redeploy, all default off until the gate passes (assistant-experience 7.5) | Flag tests; covered by ADR 0027 |

## 7. Data and corpus

| Item | Target |
|---|---|
| Frozen corpus snapshot | `evals/corpus/<snapshot_id>/` with the approved public content used by CI and evals, a manifest (portfolio commit, canonical keys, sha256), refreshed only by an explicit PR through `scripts/refresh_corpus.py` (PAA-D2: owner confirms rights; fallback is the pinned checkout used today) |
| Migrations | Forward-only, expand/contract, one explicit pre-deploy job (never at container start; existing contract), fresh-backup marker gate owned by vps-ops |
| Retention | Existing 7-day retention job covered by tests (0% today); corpus and graph pruning policy (2026-10 finding A6) measured then implemented |
| Neo4j | Kept until the spike (PAA-D12): measure the graph's marginal Recall@5 per kind with the retrieval harness; keep if multi-hop gain is at least 5 points or if the sibling needs it, otherwise move relationships to PostgreSQL (`graph_edges` plus recursive CTE) and drop a container, a vendor-findings burden and the Neo4j image digest from the deploy contract |

## 8. Skills and harness inside the repo

Skills canonical in `.agents/skills/<name>/SKILL.md`, relative symlinks in `.claude/skills/` (today inverted); each gets `evals/triggers.json` and `evals/evals.json` (see [skills.md](skills.md)). AGENTS.md shrinks to commands equal to CI, layout of non-obvious things, boundaries and the skill list; the existing owner-protection rules (no private material, no paid calls without authorization, vps-ops boundary) stay verbatim.

## 9. ADRs to write (MADR 4 in `docs/decisions/`, continuing after 0008; 0007 is an existing numbering gap recorded in the index)

| ADR | Title | Written at |
|---|---|---|
| 0009 | `src/portfolio_assistant` layout and package rename | M4 |
| 0010 | Import-linter contracts plus residual AST guard | M4 |
| 0011 | Two-tier eval design and the golden gate | M2 |
| 0012 | Layout-neutral canonical evidence keys | M1 |
| 0013 | Provider-port cassettes instead of HTTP cassettes | M2 |
| 0014 | Prompts in git with a lock file | M2 |
| 0015 | Retrieval pipeline, RRF and rule ablation | M4 |
| 0016 | Frozen public corpus snapshot | M2 |
| 0017 | Image targets `api` and `worker`, size budget | M1 |
| 0018 | Neo4j versus PostgreSQL graph | M6 (after spike) |
| 0019 | Weekly single dependency PR (supersedes `dependency-updates.md`) | M1 |
| 0020 | Contract v1.1 additive changes | M5 |
| 0021 | External tracing stays off; no hosted prompt or dataset registry | M2 |
| 0022 | `Clock` port | M4 |
| 0023 | Mutation tool choice for Python 3.14 | M2 |
| 0024 | Rich `blocks` contract and `capabilities` | M5 |
| 0025 | Opt-in per-user memory (closed schema, consent, retention, isolation) | M5 |
| 0026 | Retrieval and embedding cache, no answer cache; parallel retrieval deadlines | M4 |
| 0027 | Web access policy and runtime flags | M4 |

## 10. Migration order and why

1. Quality net before refactor (M1 to M2): P0 data fix, frozen corpus, golden, retrieval metrics, coverage and mutation gates. The refactors are only safe with a metric that fails when they hurt.
2. Containers, CI profiles, Dependabot rule (M1): independent of code layout; moving the Dockerfile first lets the later package rename update one stable file.
3. Typing widening (M3 to M4): mechanical, delegable, no behaviour change.
4. `src` rename (M4, isolated mechanical PR, one hour of agent work, followed by guards and contract regeneration). Done after typing so annotations are not reviewed twice.
5. Retrieval pipeline and domain purity (M4), measured against the baselines created in M2.
6. Contract v1.1 and conversational UX (M5), expand first; consumers adopt after.
