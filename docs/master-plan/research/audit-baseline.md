# Research: baseline audit (2026-10-24)

Planning research only. Nothing here is scheduled or authorized for execution.

Audited source: `origin/develop` at `44ae6c7` (merge of PR #123). The audit was
read-only: `git archive` export to a temporary directory, `uv sync --frozen`, and
offline commands without API keys or paid calls. The local checkout was not touched.
Paths are relative to the repository root.

Evidence labels used throughout the master plan:

- **[measured]**: output of a command or a count over the code.
- **[read]**: follows from reading code or documentation.
- **[hypothesis]**: an inference that must be measured before acting on it.
- **[source]**: a cited external practice (full list in [sources](sources.md)).

## Executive summary

**Weighted baseline: 72/100.** The repository is far more rigorous than the average
portfolio project (six layers with an AST guard, 866 tests, real services in CI,
versioned contracts, atomic cost budgets, a threat model, dated evidence). What
separates it from 95+ is not a lack of work but **measurable AI quality, concentrated
complexity and showcase readability**:

1. **Retrieval quality is not measured.** `evals/retrieval.json` has **9 cases**; there
   are no labelled qrels and no Recall@k ("No Precision/Recall@k claim is made without
   labelled relevance judgements", `docs/verification/live-depth-2026-10-10.md`). The
   documented target (Recall@5 ≥ 95%, `docs/assistant-evaluation.md`) has no harness
   that computes it.
2. **Weak spot in English (and in lexical recall in general):** the full-text index uses
   `to_tsvector('simple', content)` (`migrations/004_semantic_knowledge.sql`) and
   `websearch_to_tsquery('simple', …)` (`app/adapters/retrieval.py:78`): no stemming,
   no stopwords and no `unaccent`. The two direct lexical/vector failures in the
   baseline are EN queries (`project`, `role`, `vector` strategy,
   `docs/verification/retrieval-after.json`).
3. **`PublicRetrieval.search` has cyclomatic complexity 48** [measured, ruff C901], with
   hardcoded keyword lists, regexes over TypeScript syntax (`company:\s*"…"`) and
   path-based boosts (`/profile.ts`, `/education.ts`). This is *overfitting* to the
   corpus and to the suite: every new case adds an `if`. In addition,
   `app/domain/fixture.py` parses TS format inside the **domain**.
4. **There is no LLM-as-judge and there are no human labels** (`human_scores null`,
   `live_quality_verified false`): live answer quality has no reproducible number.
5. **Incomplete supply chain in a public repository:** GitHub secret scanning and push
   protection **disabled** [measured, API], no CodeQL/SAST, no SBOM and no image
   attestation; Neo4j 5.26.32 with 1 CRITICAL, 4 fixable HIGH and 107 HIGH without a
   fix (current policy: advisory).
6. **Overloaded showcase:** 34 docs + 46 reports in `docs/verification/`, a README with
   6+ paragraphs of legal caveats before and after the value; no CHANGELOG, CODEOWNERS,
   CODE_OF_CONDUCT or published releases; ADR 007 gap.

**Target state (summary):** the same six-layer architecture (kept), with retrieval
decomposed into a declarative pipeline and evaluated with bilingual qrels (≥ 150
queries) against a **frozen snapshot of real embeddings** that allows measuring
Recall@5/nDCG@5 in CI without paid calls; a judge calibrated against ≥ 120 human
labels (κ ≥ 0.7); separate regression/capability/red-team suites; versioned prompts
with a hash in every run; mypy strict across `app/`; Hypothesis + mutation testing in
domain/application; Locust with TTFT metrics; "build once" CI with SBOM + provenance;
a showcase README with real eval numbers.

**Roadmap:** P0 security/hygiene quick wins (1–2 days) → P1 eval foundation → P2
retrieval/prompts/async refactor → P3 testing depth → P4 CI/CD and supply chain → P5
showcase and docs → P6 live evaluation and Neo4j decision (requires authorization and
budget). See [roadmap](../roadmap.md).

## Command evidence (offline, temporary export)

| Command | Result | Time |
|---|---|---|
| `uv sync --frozen` | OK (local uv 0.12.10; the repo requires 0.13.1 in README/CI) | — |
| `uv run ruff check .` / `ruff format --check .` | All checks passed / 272 files formatted | 0.8 s |
| `uv run mypy` (configured scope: 39 files) | Success | 22 s |
| `uv run mypy app --strict` (all of `app/`) | **199 errors in 38 files** (adapters/postgres 50, bootstrap/container 41, presentation/http 37, adapters/portfolio 25) | — |
| `uv run pytest --co -q` | **866 tests** | 11.6 s |
| `pytest -m "not integration"` | **819 passed, 47 deselected** | 21.7 s |
| coverage (unit only, statements) | **80% total**; domain 89%, application 91%, ai 91%, presentation 89%, bootstrap 85%, adapters 68%, entrypoints 19% | — |
| `ruff --select B,S,ASYNC,SIM,C90,PL,RUF,PERF,FBT,ANN,TRY,…` (probe) | 470 findings (ANN 247, TRY003 95, PLR2004 62, **C901 11**) | — |
| C901 > 10 | `ai/retrieval.search` **48**, `adapters/portfolio/indexing._sync` 28, `bootstrap/config.safe_configuration` 26, `create_app` 21, `domain/fixture.fixture_message` 21, `lifespan` 19 | — |
| CI `quality.yml`, last 15 runs | 3.3–4.2 min wall; 0 failures (3 cancelled by concurrency) | — |
| Jobs (run 39187338273) | Database 206 s, Container 143 s, Static 32 s, Secrets 6 s, Workflows 5 s | — |
| Branch protection `develop` | Required check `Required checks` (strict), conversation resolution, enforce admins; 0 reviews | — |
| Repository security_and_analysis | Dependabot security updates ON; **secret scanning OFF, push protection OFF** | — |

Size [measured]: `app/` 8,673 Python LOC (95 modules), `tests/` 11,150 LOC,
`scripts/` 4,821 LOC (27 scripts), 9 SQL migrations, 20 files in `contracts/`, 16 in
`evals/`.

## Detailed findings by axis

The baseline score per axis is in the [scorecard](../scorecard.md).

### Code quality

- `app/ai/retrieval.py` (399 LOC): ad hoc RRF fusion (`weight / (10 + index)`, k=10,
  weights 3.0/0.1 when there are no semantic embeddings) followed by ~10 conditional
  keyword re-orderings (`'degree','graduated',…,'estudou'`, which includes
  Portuguese), regexes over the TS source (`company:\s*"…"`, `startedOn:`) and
  path anchors. It makes it impossible to reason about the effect of a change without
  running the whole suite; it is the main risk of silent regression.
- `app/domain/fixture.py` (271 LOC) and `app/domain/evidence.py` contain regexes for the
  portfolio content format: the domain knows an external file format. It should live in
  `adapters/portfolio` (parsing) and `adapters/providers/fixture` (fake provider).
- `app/adapters/providers/answer.py`: the system prompt is a concatenated string with no
  id/version/hash.
- Ruff selects only `I, N, UP` and a subset of `D`; `flake8-bugbear` is configured
  (`extend-immutable-calls`) but **`B` is not selected**: dead configuration.
- Exceptions with vanilla messages (TRY003 ×95) and magic values (PLR2004 ×62):
  acceptable noise, but missing ANN annotations in adapters/presentation prevent global
  mypy strict.

### Architecture

Details in [target architecture](architecture.md).

- Strengths: the dependency rule is enforced by AST with detection of
  `__import__`/`importlib`/`exec`; the domain is stdlib-only; `Protocol` ports in
  `application/`; adapters per technology (`postgres/`, `neo4j/`, `providers/`,
  `portfolio/`, `observability/`); bootstrap as the only composition root; ADR 001 and
  006 document the reasons.
- Weaknesses: `ai` imports `application.answer.generate` (a function that performs I/O
  through the injected provider; correct in direction, but it couples orchestration and
  use case); the LangGraph graph is linear with 2 nodes (`retrieve → answer`) with
  citation validation outside the graph; synchronous persistence through `to_thread`
  (≥ 15 call sites) while the checkpointer uses `AsyncConnectionPool`.

### Tests

- Very good regression culture (for example `test_live_depth_regressions.py`,
  cancellation probes with a silent provider). Structure is missing: unit/integration/
  contract are mixed per file, and the `integration` marker is the only axis.
- Adapter coverage of 68% in unit tests is expected (integration covers them), but
  **combined coverage is not measured** and there is no gate.

### Eval quality

- Excellent bank design (families, holdout without leakage, adversarial cases,
  multi-turn). The gap is *measurement*: retrieval with 9 binary cases (pass/fail by path
  + `contains`) and no graded relevance; generation without a validated automatic scorer;
  live reports with raw answers that are not versioned (correct for privacy) but without
  aggregate metrics that are comparable across versions.
- Fixture embeddings are a 64-dimension hash (`hash64-v1`): CI never measures real
  semantic recall.

### Security

- Solid application controls (see `docs/threat-model.md`). Prompt: context marked as
  `untrusted_*` and anti-override rules, which is good OWASP LLM01 practice.
- Findings: native secret scanning is off (free on public repositories); a one-script
  in-house scanner is the only control; no CodeQL; no `dependency-review-action` on PRs;
  no pip-audit/osv over `uv.lock` (the image Trivy scan covers it partially); the
  runtime image includes `git` for the sync CLI (extra surface in the web process); the
  Neo4j vendor image has open findings
  (`docs/verification/neo4j-release-blocker-2026-10-17.md`).

### Performance, latency and cost

- Cost: `Budget` in the domain with Decimal, reserve→settle, hard cap of USD 10
  validated in configuration. Very good. Missing: *cost per answer* reported by evals
  and token p95.
- Latency: no written SLO; no load test; graph retrieval is 3× slower than hybrid in
  the fixture artifact.

### Observability

- No transcripts by design (privacy): correct and a differentiator. Missing: aligning
  names with the OTel GenAI semantic conventions (`gen_ai.request.model`,
  `gen_ai.usage.input_tokens`, …) so that any backend (Grafana, Langfuse, Phoenix)
  understands them, and exposing `prompt_version`/`corpus_version` as low-cardinality
  attributes.

### CI reliability

- Excellent discipline (SHA pins, input identity through `ci_identity`, a single gate).
  Costs: both heavy jobs repeat the Neo4j service, the pinned portfolio checkout,
  `uv sync`, the Postgres build, `app.migrate` and `knowledge_sync` (~60–90 s
  duplicated). `database` installs Node + `npm ci` of the backoffice for the IAM fixture
  (25 s).

### Docs and showcase (recruiter lens)

- 30 s: the hero is good ("A grounded conversation about Gonzalo's work"), but the
  "Current state" block with 5 negations appears before any achievement. A recruiter
  reads "disabled, not provisioned, not authorized, advisory findings" before "hybrid
  GraphRAG".
- 5 min: there is no *results* table (Recall@5, citation support, TTFT, cost per
  answer). The evidence exists but is spread across 46 dated reports.
- 30 min: good ADRs but without MADR format and without homogeneous status/
  consequences; 007 is missing.

### API UX (designer lens)

- SSE: 7 events with `sequence`, `schema_version`, explicit terminals
  (`run.completed`, `run.failed`, `run.cancelled`) and "a broken connection is not
  completion": an honest contract.
- Weak: `run.status` only has the `evidence_found` phase (poor perceived progress during
  1–3 s of retrieval + TTFT); `FailedPayload.code` is a free `string` (the frontend
  cannot map it exhaustively); no `retryable`/`retry_after`; `ErrorBody.message`
  defaults to `code.replace('_', ' ')` (`app/presentation/middleware.py:24`), giving
  "rate limited", which is neither localized nor actionable; it is not RFC 9457.

### DX

- The keyless demo is real and works, but it requires choosing ports, `source`-ing an
  env script and 8 commands. A `just demo` (or `make demo`) with ephemeral ports would
  bring time-to-first-answer down to one command.

## Reference files cited by the research

`pyproject.toml`, `.github/workflows/quality.yml`, `.github/dependabot.yml`,
`infra/docker/app/Dockerfile`, `scripts/check_architecture.py`,
`tests/test_architecture.py`, `app/ai/retrieval.py`, `app/ai/workflow.py`,
`app/adapters/retrieval.py`, `app/adapters/providers/answer.py`,
`app/domain/fixture.py`, `app/presentation/middleware.py`, `app/presentation/http.py`,
`app/bootstrap/config.py`, `migrations/004_semantic_knowledge.sql`,
`contracts/sse.schema.json`, `contracts/openapi.json`, `evals/retrieval.json`,
`docs/verification/retrieval-after.json`, `docs/assistant-evaluation.md`,
`docs/conversation-evaluation.md`, `docs/verification/live-depth-2026-10-10.md`,
`docs/verification/neo4j-release-blocker-2026-10-17.md`,
`docs/adrs/001-dependency-direction.md`, `CONTRIBUTING.md`, `SECURITY.md`,
`AGENTS.md`, `README.md`, `.claude/skills/*/SKILL.md`.
