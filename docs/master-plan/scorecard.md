# Scorecard

Rubrics: [rubrics.md](rubrics.md) (ecosystem rubrics v2, frozen). Baseline: `origin/develop` `e749ca7`, 2026-11-09. Evidence: [audit.md](audit.md). Rule from the rubric: a criterion without evidence is unmet; 95-100 means every criterion met with evidence; 85-94 means every critical criterion (C) met; below 85 means a C criterion is unmet. Caps: a failing required check caps the lens at 70; a committed secret caps Security at 40; a contract break without a major path caps Architecture at 60.

**How to read the baseline.** Axes marked *auto* are computed from measured numbers by the rubric rules. Axes marked *judged* are the planner's score anchored to cited evidence; they are replaced by the first independent evaluator-agent score at M3 (rubric: evaluators never see the planner's reasoning). The baseline replaces the v1 weighted score of 72 (v1 used ten different axes and weights; v2 does not weight or average across axes).

## 1. Lens 1: senior developer

| Axis | Baseline | Basis | Target | Why not higher today (unmet critical criteria) |
|---|---|---|---|---|
| D1 Architecture | **82** judged | Six layers, AST guard with negative probes, empty violation baseline, composition root in `bootstrap`, 32 `Protocol` references; but guard is custom (no import-linter contracts), domain parses portfolio TypeScript, `ai` layer imports application functions, mypy covers 41% of files | 95 | Guard lacks `forbidden`/`independence` contracts; domain not format-free |
| D2 Code quality | **58** auto | `mypy --strict app`: 199 errors, scope 39/95 files; C901 above 10 in 11 functions (max 48); no dead-code check; ecosystem ruff families not selected | 95 | Zero type errors, complexity at most 10, dead-code check |
| D3 Tests | **66** auto | 866 tests; 2 integration failures in the audit run (cap 70 applied until CI conditions are shown green); coverage 77.6% line, 68.7% branch against 85% floor; no diff-coverage, mutation, property, flake detection | 95 | Branch floor, diff coverage 90%, mutation score, 0 failing |
| D4 CI/CD | **70** judged | Aggregate gate exists, SHA-pinned; not dynamic, duplicated setup, no build-once, weekly single-PR rule violated | 95 | Dynamic affected-only profiles, weekly single PR, build once and deploy same digest |
| D5 Security and supply chain | **68** judged | Threat model, non-root image with digest pins, in-house secret scan, Trivy gate; no CodeQL, SBOM, provenance, zizmor, dependency-review; `pull_request_target` workflow; 4 fixable HIGH image findings | 95 | CodeQL, SBOM plus provenance, zizmor, vulnerability SLA, fixable HIGH at 0 |
| D6 Performance | **62** judged | Atomic spend, run timeout, SSE heartbeat, query-plan benchmarks; no enforced latency/TTFT/cost budget, no load test, image 992 MB | 95 | Budgets enforced in CI (stubbed-model load, cost and latency on recordings, image size ratchet) |
| D7 Observability | **72** judged | Private status and metrics, Prometheus, opt-in OTLP with allowlist, per-stage timing; no `gen_ai.*` centralization, no run-to-trace id correlation test, no SLO definitions | 90 floor, 95 after Phase V | SLO burn alerts and real dashboards need the VPS |
| D8 Docs and DX | **64** judged | README 339 lines, 34 docs plus 46 dated reports without hierarchy, 7 ADRs, no CHANGELOG, no community files beyond SECURITY, skills without evals, no task runner | 95 | README template, MADR current, one-command setup, CHANGELOG, community files, skill activation evals |

## 2. Lens 2: senior product designer, API and conversational UX

| Axis (API meaning) | Baseline | Basis | Target | Note |
|---|---|---|---|---|
| P1 Error and response contract clarity | **78** judged | Typed errors and closed SSE terminal events; messages not enumerated, no `retryable`, no RFC 9457 `type`; EN and ES copy partly in the consumer | 95 | Additive v1.1 (PAA-D17) |
| P2 Streaming UX | **80** judged | First delta 75-206 ms in fixture mode (audit), heartbeat 15 s, cancel and disconnect handled; few progress phases | 95 | Time to first token budget on live recordings needs paid calls |
| P3 Assistant message quality | **50** judged | No golden set, 1,000 cases never answer-reviewed, no validated judge, language policy tested only in fixture mode, retrieval eval stale (P0-1) | 95 (provisional 90 until the owner's 20% spot check) | Recording, snapshot and judge runs are pre-authorized within the DR-04 caps; the only dependency is the owner's one-time 20% spot check of the agent-bootstrapped labels (DR-05), which validates the judge |
| P4 Contract docs and examples | **80** judged | OpenAPI, SSE schema, examples, frontend handoff; no breaking-change gate, no Schemathesis | 95 | oasdiff plus Schemathesis in CI |
| P5 Consistency with consumers | **74** judged | Byte comparison with backoffice contracts, consumer pinned at a SHA; no scheduled cross-repo compile job | 95 | Cross job (ecosystem 18.1) |
| P6 Consistency and identity across the two APIs | **70** judged | Near-duplicate CI, Dockerfile and skills with the sibling; no shared template, naming and health endpoints differ | 95 | Standards templates, aligned health contract |

## 3. Lens 3: senior recruiter (public showcase)

| Criterion | Baseline | Evidence |
|---|---|---|
| First-screen clarity | 60 | README opens with value but caveats precede results; 339 lines |
| Proof (measured results) | 55 | No results table; evidence is dated reports that say "pending review" |
| Writing quality | 72 | Dense; defensive qualifiers |
| Credibility | 80 | Real architecture, tests, threat model; honest limits |
| Calls to action | 55 | No release, no demo command shorter than 8 steps |
| Polish | 70 | Gallery screenshots exist; no badges policy, no CHANGELOG |
| Differentiation | 85 | Evidence-grounded RAG with graph provenance, atomic spend cap, SSE contract |
| **Lens score** | **66** judged | Minimum-anchored; target 95 |

## 4. Targets and the explicit floors

| Axis | Target | Floor and reason |
|---|---|---|
| All axes except those below | 95 | none |
| D7 Observability | 95 | **90** until the VPS exists (Phase V): SLO burn alerting, dashboards and online evals cannot be exercised without a deployed service |
| P3 Assistant message quality | 95 | **90 provisional** until the owner completes the one-time 20% spot check of the bootstrapped judge labels (DR-05); the judge is then validated and judged quality counts. Recording, embeddings snapshot and judge runs are pre-authorized within the DR-04 caps (USD 2 per campaign, USD 8 per month), so P3 is not blocked by spend; only exceeding a cap needs the owner. Reasoning for 90 and not 95: the judged part of P3 (tone, completeness) is unvalidated without that spot check, so credit stops at the deterministic gate |
| D6 Performance (live part) | 95 | Offline budgets (stubbed model, recordings) are enough for 95; live TTFT and cost p95 are an extra row in Phase V |

## 5. Automatic measurement

`scorecard/` (Python package, `uv run python -m scorecard`) aggregates CI artifacts into `scorecard.json`: per-axis inputs and pass or fail per criterion of rubrics v2, nightly and on release; it exits non-zero on regression against `scorecard/ratchets/scorecard.json`. Judgement axes are filled from `docs/evidence/scores/<date>.md` written by the independent evaluator agent.

| Axis | Criterion IDs and automatic inputs | Source artifact |
|---|---|---|
| D1 | `D1.guard_violations == 0`, `D1.negative_fixtures_pass`, import-linter contracts kept, domain and application stdlib-only | `artifacts/arch.json` |
| D2 | `D2.mypy_errors == 0` over `src/`, `D2.ruff_findings == 0`, `D2.max_cc <= 10`, `D2.dead_code == 0` (vulture) | `artifacts/static.json` |
| D3 | `D3.branch_coverage >= floor`, `D3.diff_coverage >= 90`, `D3.mutation_score >= target` per package, `D3.flaky_30d == 0` | `coverage.xml`, `mutmut` results, flake report |
| D4 | `D4.pr_p50`, `D4.pr_p95` within budget, `D4.single_dependabot_pr`, `D4.build_once_digest` | `gh run list --json`, guard report |
| D5 | `D5.pinned_actions == 100%`, `D5.zizmor_high == 0`, `D5.codeql_open_high == 0`, `D5.sbom_attested`, `D5.provenance_verified`, `D5.fixable_high == 0`, `D5.secrets == 0` | zizmor SARIF, `gh attestation verify`, Grype JSON |
| D6 | `D6.ttfe_p95_stubbed`, `D6.error_rate`, `D6.rss_growth`, `D6.answer_cost_p95_recorded`, `D6.image_mb <= ratchet` | Locust report, eval report, `docker image inspect` |
| D7 | `D7.log_redaction_test`, `D7.request_id_propagation_test`, `D7.health_contract`, SLO definitions file present | pytest results |
| D8 | `D8.readme_headings`, `D8.links_ok`, `D8.adr_index`, `D8.changelog_current`, `D8.community_files`, `D8.skill_trigger_accuracy`, `D8.agents_commands_match` | docs checks, skills evals |
| P1-P6 | `P1.problem_schema_valid`, `P2.ttft_budget`, `P3.golden_pass == 100%` (cassette), `P3.full_set_metrics` (reported), `P4.oasdiff_clean`, `P4.schemathesis`, `P5.consumer_compile`, `P6.standards_drift == 0` | eval report, oasdiff, cross job |
| Recruiter | `R.readme_lines <= 250`, results table dated within 30 days of release, release exists, one-command demo timed | docs checks, release workflow |

## 6. Ratchet files (only tighten; loosening needs an ADR and the owner)

| File | Holds |
|---|---|
| `scorecard/ratchets/static.json` | mypy error count, ruff findings per rule, files outside strict scope, max complexity, vulture count |
| `scorecard/ratchets/tests.json` | line and branch coverage per layer, diff-coverage floor, mutation score per package, test counts per lane |
| `scorecard/ratchets/ci.json` | duration budgets p50 and p95 per profile |
| `scorecard/ratchets/image.json` | image size in MB, fixable HIGH count, layer count |
| `evals/baselines/golden.json` | per-stratum pass counts (must stay 100%), item counts per stratum and locale |
| `evals/baselines/full.json` | per-family and per-locale metrics of the last accepted full run, EN-ES gap |
| `evals/baselines/retrieval.json` | Recall@5, nDCG@5, MRR@10 per strategy, locale, family; the absolute floor |
| `evals/baselines/budgets.json` | latency, TTFT, tokens, cost p95 of the last accepted recording |
| `scorecard/ratchets/scorecard.json` | last accepted axis scores |

## 7. Re-score cadence

| Cadence | What |
|---|---|
| Every PR | Static, tests, golden cassette lane (profile `assistant-quality`), ratchet checks |
| Nightly | Full mutation (scoped), flake detector, Schemathesis long run, stubbed SSE load, osv, Scorecard job, `scorecard.json` and regression check |
| Weekly | Dependabot PR and guard, link check, drift check, CI duration report, Scorecard |
| Monthly | Judge calibration re-run (once a judge exists), skill staleness, flaky review, quarantine review |
| Per release | Full set run (on demand tier) with report in the PR, independent evaluator scores for judged axes, live golden pass^3 (pre-authorized within DR-04 caps) |
| Quarterly | Golden set review (add incident items, retire with reason), independent re-audit, standards review, token rotation |

## 8. Forecast by milestone (expectations, credited only with measured evidence)

| Axis | M0 | M2 | M3 | M4 | M6 |
|---|---|---|---|---|---|
| D1 | 82 | 84 | 85 | 96 | 96 |
| D2 | 58 | 70 | 82 | 96 | 96 |
| D3 | 66 | 90 | 92 | 94 | 96 |
| D4 | 70 | 90 | 94 | 95 | 96 |
| D5 | 68 | 88 | 92 | 95 | 96 |
| D6 | 62 | 85 | 90 | 94 | 95 |
| D7 | 72 | 76 | 80 | 84 | 90 |
| D8 | 64 | 72 | 92 | 94 | 96 |
| P1 | 78 | 78 | 80 | 80 | 95 (M5) |
| P2 | 80 | 80 | 82 | 84 | 95 (M5) |
| P3 | 50 | 85 | 88 | 90 | 95 (90 until spot check) |
| P4 | 80 | 92 | 94 | 95 | 96 |
| P5 | 74 | 80 | 90 | 94 | 95 |
| P6 | 70 | 80 | 90 | 95 | 95 |
| Recruiter | 66 | 70 | 90 | 92 | 96 |

**Milestone acceptance rule.** A milestone is reached only if `scorecard.json` shows every axis at or above its forecast in the nearest column at or before that milestone (M1 uses M0, M5 uses M4, M7 uses M6; D7 and P3 use their stated floors), or the axis has a newer independent evaluator score at or above it (evaluator scores replace judged numbers from M3). A missed axis blocks the checkpoint tag until a gap list with owner task IDs is in `progress.md`.
