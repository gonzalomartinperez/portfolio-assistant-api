# Scorecard

Scores are 0–100, assigned with the fixed [rubrics](rubrics/) and backed by the
automated measurements below. Baseline: `origin/develop` at `44ae6c7`, audited
2026-10-24 ([baseline audit](research/audit-baseline.md)).

## Axes, baselines and targets

| Axis | Lens | Weight | Baseline | Research target | Owner target | Main baseline evidence |
|---|---|---|---|---|---|---|
| Code quality | developer | ×1 | **72** | 95 | ≥ 95 | minimal ruff (no B/S/SIM/C90/ANN), `search` CC 48, hardcoded keywords and TS regexes, ~1 KB inline prompt in `adapters/providers/answer.py`, `domain/fixture.py` with TS-format knowledge |
| Architecture | developer | ×1.5 | **80** | 96 | ≥ 95 | six layers + AST guard with bypass probes, 19 `Protocol` ports, composition root; weak: mypy strict only on inner layers, sync DB through `asyncio.to_thread` mixed with an async pool, loose entrypoints in `app/*.py`, `ai/` imports application functions (`generate`) instead of receiving capabilities |
| Tests | developer | ×1 | **74** | 95 | ≥ 95 | 866 fast tests, real services in CI, cancellation/SIGTERM probes; missing: coverage gate, branch coverage, Hypothesis, mutation, layout by type (52 flat files), `application/conversations.py` 55% |
| Eval quality (RAG) | developer | ×1.5 | **58** | 95 | ≥ 95 | 1,000-question bank split by family, 40 adversarial, 300 documented live turns; missing: qrels (9 retrieval cases), Recall@k/nDCG, validated judge, formal regression/capability suites, eval on PRs |
| Security | developer | ×1 | **76** | 95 | ≥ 95 | threat model, CSRF, sessions with ownership, non-root image with digests, gated Trivy, in-house secret scanner; missing: GitHub secret scanning/push protection, CodeQL, dependency review, SBOM/attestation, VEX; Neo4j open findings; `git` in the runtime image |
| Perf / latency / cost | developer | ×1 | **70** | 95 | ≥ 95 | atomic spend reservations, USD 10/month cap, `run_timeout_seconds=60`, 15 s SSE heartbeat, query-plan benchmarks; missing: load test, TTFT/p95 SLOs, measurement under concurrency; fixture retrieval p50 ~280 ms hybrid and 824 ms graph |
| Observability | developer | ×1 | **72** | 94 | ≥ 95 | private status/metrics, Prometheus, opt-in OTLP with allowlist, per-stage `phase()`; missing: OTel GenAI semconv, run_id↔trace correlation, versioned dashboards/SLOs, prompt/corpus version in metrics |
| CI reliability | developer | ×1 | **82** | 96 | ≥ 95 | SHA-pinned actions, aggregate gate, `merge_group`, concurrency, 4 min; weak: duplicated Postgres build+migrate+index in `database` and `container`, no coverage/junit summary, no flake detection, no build-once image |
| Docs / showcase | recruiter | ×1 | **66** | 96 | ≥ 95 | README with real gallery and diagrams; 7 ADRs; weak: defensive tone, 80 doc files without Diátaxis hierarchy, dated evidence mixed with living docs, no CHANGELOG/releases, ADR 007 missing, no eval numbers in README |
| DX | developer | ×1 | **74** | 95 | ≥ 95 | uv + fixture mode + `scripts.demo`; weak: 8-command quickstart with port exports, no task runner, no pre-commit, no devcontainer, uv version inconsistent with the installed one |
| **Weighted** | — | — | **72** | **95+** | ≥ 95 | weights: AI quality (eval) and architecture ×1.5; the rest ×1 |

The weighted score is `Σ(weight × score) / Σ(weight)` with a weight sum of 11.

Lens scores (separate from the axes, each 0–100 from its rubric):

| Lens | Rubric | Baseline | Owner target |
|---|---|---|---|
| Senior developer | [senior-developer.md](rubrics/senior-developer.md) | the axis table above (weighted 72) | ≥ 95 |
| Senior designer (API/streaming UX) | [senior-designer.md](rubrics/senior-designer.md) | not yet scored numerically; qualitative findings in the [audit](research/audit-baseline.md#api-ux-designer-lens) | ≥ 95 |
| Senior recruiter (public showcase) | [senior-recruiter.md](rubrics/senior-recruiter.md) | not yet scored numerically; closest axis is Docs/showcase 66 | ≥ 95 |

**Owner requirement vs. research targets.** The owner requires 95+ on every axis. The
research target for Observability is 94 and reaches 95 only in P6; Eval quality tops
out at ~90 without P6. Both therefore depend on P6 authorization and, for online parts,
on the VPS.

## Expected score by phase

| Axis | Base | P0 | P1 | P2 | P3 | P4 | P5 | P6 |
|---|---|---|---|---|---|---|---|---|
| Code quality | 72 | 76 | 77 | 93 | 94 | 94 | 95 | 95 |
| Architecture | 80 | 80 | 81 | 95 | 95 | 96 | 96 | 96 |
| Tests | 74 | 76 | 80 | 84 | 95 | 95 | 95 | 95 |
| Eval quality | 58 | 58 | 85 | 87 | 88 | 88 | 90 | 95 |
| Security | 76 | 86 | 86 | 88 | 90 | 95 | 95 | 96 |
| Perf/latency/cost | 70 | 70 | 74 | 82 | 92 | 92 | 92 | 95 |
| Observability | 72 | 72 | 75 | 88 | 89 | 92 | 94 | 95 |
| CI reliability | 82 | 85 | 87 | 88 | 92 | 96 | 96 | 96 |
| Docs/showcase | 66 | 72 | 74 | 76 | 78 | 82 | 96 | 97 |
| DX | 74 | 78 | 79 | 85 | 88 | 92 | 95 | 95 |

These are research expectations, not results. A phase is credited only with the
measured evidence below.

## Automated measurement

Each axis has measurable inputs. Commands marked *exists* run today; *planned* items are
introduced by the named phase. The rubric reviewer reads these outputs; numbers are not
converted into scores mechanically.

| Axis | Measured inputs | Command / source | Status |
|---|---|---|---|
| Code quality | ruff findings by rule, C901 count > 10, mypy strict error count | `uv run ruff check app tests contracts scripts`; `uv run ruff check --select C90 app`; `uv run mypy app --strict` | exists (strict scope and extended selection planned, P0/P2) |
| Architecture | guard violations, probe results, `to_thread` count in adapters, per-layer third-party allowlist | `uv run python -m scripts.check_architecture`; `grep -rc to_thread app/adapters` | guard exists; extended rules planned (P2) |
| Tests | test count, combined branch coverage per layer, diff coverage, mutation score per layer, Hypothesis property count | `uv run pytest -q`; coverage + `diff-cover`; `mutmut` nightly | partial; gates planned (P0 measure, P3 gate) |
| Eval quality | Recall@5, nDCG@5, MRR@10, Hit@1 per locale × kind × strategy; EN–ES gap; regression pass rate; judge κ/TPR/TNR; live capability metrics | `scripts/evaluate_retrieval.py --metrics` (ranx); regression suite; capability suite | planned (P1; live P6) |
| Security | secret-scanning alerts, CodeQL high count, dependency-review result, osv/pip-audit findings, Trivy gate, OpenSSF Scorecard score | GitHub security APIs; CodeQL; `osv-scanner`; Trivy; Scorecard | Trivy and in-house scanner exist; rest planned (P0/P4) |
| Perf / latency / cost | retrieval p95, API overhead to first delta p95, TTFT p50/p95, full-answer p95, cost per answer p95, monthly ledger | Locust + `phase()`; capability suite; ledger | ledger exists; load and SLOs planned (P3/P6) |
| Observability | GenAI semconv attribute coverage, `prompt_version`/`corpus_version` presence, run_id↔trace correlation | OTLP fixture receiver payload review | planned (P2/P4) |
| CI reliability | PR wall p95, per-job duration, failure and flake rate (nightly ×3), duplicated setup time | `gh run list` / job timings | data exists; summary planned (P4) |
| Docs / showcase | README length (≤ 250 lines), results table present with date/commit, broken links, Diátaxis placement, ADR numbering continuity | rubric review + link check | planned (P0/P5) |
| DX | commands to first fixture answer, time to first answer, uv version consistency | `just demo` timing | planned (P0/P5) |

A future `scripts/scorecard` report that gathers these inputs into one dated JSON file
under `docs/evidence/` is a candidate P4/P5 item; it does not exist yet.
