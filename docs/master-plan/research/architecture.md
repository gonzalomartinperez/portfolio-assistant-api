# Research: target architecture (refined Clean/Hexagonal)

Planning research only. Proposed ADR numbers are reservations for future decisions,
not accepted ADRs. Labels follow the [baseline audit](audit-baseline.md).

## What is kept (do not touch)

- The **six layers** and their names (`domain`, `application`, `ai`, `adapters`,
  `presentation`, `bootstrap`) and the AST guard with bypass probes: it is better than
  import-linter for the "domain stdlib-only" rule because it detects dynamic imports.
- Ports as `typing.Protocol` in `application/` (structural typing, no ABCs) [source:
  Cosmic Python, PEP 544].
- A single composition root in `bootstrap/container.py` without a DI framework.
- Frozen v1 contracts (`contracts/`), explicit SQL migrations with checksums, fixture
  mode by default, evidence with commit SHA + line range.

## What changes

| # | Change | Why | ADR |
|---|---|---|---|
| A1 | `app/ai/retrieval.py` → package `app/ai/retrieval/` with a pipeline: `query_analysis.py` (deterministic intent classifier → `QueryIntent` dataclass), `candidates.py` (lexical/vector/graph through a port), `fusion.py` (standard RRF k=60, parameterizable), `rules.py` (**declarative** boosts loaded from `app/ai/retrieval/rules.toml`), `selection.py` (top-k + per-document diversity) | CC 48 → ≤ 10 per function; every rule testable and measurable by ablation in the retrieval suite | ADR-009 |
| A2 | Portfolio format parsing leaves the domain: `domain/fixture.py` → `adapters/providers/fixture_answer.py`; regexes from `evidence.py`/retrieval → `adapters/portfolio/structured.py`, which produces typed `Fact`/`Entity` at indexing time. Retrieval operates on structured metadata (`company`, `started_on`, `kind`), not on TS text | A truly pure domain; robustness against portfolio layout changes (there has already been a layout handoff) | ADR-010 |
| A3 | Prompts as versioned artifacts: `app/ai/prompts/answer.v3.md` + `registry.py` (`PromptSpec(id, version, sha256)`); the adapter receives the rendered prompt; `prompt_version` is persisted in `runs` and emitted in metrics/evals | Prompt→quality traceability; eval diffs per PR | ADR-011 |
| A4 | Explicit LangGraph graph: `analyze → retrieve → (clarify \| answer) → validate_citations`, with `validate` as a node (today it is outside) and a conditional edge for abstention/clarification | Shows real LangGraph use (recruiter) and isolates the grounding policy (developer) | ADR-012 |
| A5 | Native async persistence: `psycopg` `AsyncConnectionPool` for everything and `neo4j.AsyncGraphDatabase`; remove `asyncio.to_thread` from adapters | A single concurrency model; real query cancellation; fewer threads under load | ADR-013 |
| A6 | Additive error contract v1.1: `code` as an `enum` in OpenAPI and SSE, optional fields `retryable: bool`, `retry_after_s: int`, `type` (RFC 9457-style URI); human EN/ES messages per code in `presentation/messages.py`. Future v2: full `application/problem+json` | Actionable error UX without breaking v1 | ADR-014 |
| A7 | `run.status` with additional phases (`understanding`, `retrieving`, `evidence_found`, `writing`), additive in `StatusPayload.phase` | Perceived progress; the frontend can show "Searching projects…" | in ADR-014 |
| A8 | Entrypoints `app/{main,migrate,retention,knowledge_sync,knowledge_watch}.py` → `app/bootstrap/cli/` (or `app/entrypoints/`) with `[project.scripts]` in `pyproject.toml` | A clear surface; removes the `ENTRY_POINTS` exception from the guard | — |
| A9 | `src/` layout: `app/` → `src/portfolio_assistant/` | PyPA practice; avoids accidental imports from the cwd. **Optional**, high churn; do it in an isolated mechanical PR or do not do it | ADR-015 (to decide) |
| A10 | Web process without `git`: sync uses the image with the `worker` target (multi-stage), which does include git | Smaller surface in the exposed container | in ADR-013 |

## Guard rules (extension)

Add to `scripts/check_architecture.py` (with probe tests, as today):

1. Independence between adapters: `adapters.postgres` does not import `adapters.neo4j`
   or vice versa (only `adapters.retrieval` composes them, or better: move the
   composition to bootstrap).
2. `presentation` does not import `ai` (already implicit) or `langgraph`/`openai`/
   `psycopg` (third-party allowlist per layer: `presentation` → fastapi, pydantic;
   `adapters` → drivers; `ai` → langgraph, langchain-core).
3. `ai` does not import drivers (`psycopg`, `neo4j`, `openai`, `httpx`).
4. Ratchet: mypy strict per layer with a baseline that can only go down (`mypy --strict`
   in CI over all of `app/` with justified `# type: ignore[code]`, target 0).

## Async boundaries (written rule)

- All request-path I/O is `async`; no blocking `def` is called without `to_thread`, and
  the target is zero `to_thread` in adapters (A5). Bounded CPU-bound work (Lingua) may
  stay synchronous if p95 < 5 ms [measured in docs: warm p95 3.4 ms].
- Cancellation: `aclosing` + `asyncio.timeout` per phase; `CancelledError` is never
  swallowed (already in CONTRIBUTING; add the ruff `ASYNC` and `BLE001` rules).

## ADRs to write (MADR 4.0)

ADR-007 (stub: "number reserved/retired", to close the gap), 009 declarative retrieval
pipeline, 010 structured corpus projection, 011 prompt registry, 012 graph with
validation as a node, 013 async persistence and web/worker split, 014 error/SSE v1.1,
015 src layout (decision), 016 evaluation: qrels + embeddings snapshot + calibrated
judge, 017 Neo4j: keep (CalVer) vs graph in Postgres (data-driven decision from a spike,
see [AI quality](ai-quality.md#offline-vs-online-and-tooling)), 018 vulnerability
policy with VEX and SLA.
