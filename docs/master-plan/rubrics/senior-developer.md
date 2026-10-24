# Rubric: senior developer (v1)

Focus from the research: correctness, design, testability, operability, supply chain.

Score each axis 0–100 with the anchors below, then compute the weighted developer
score: Architecture and Eval quality ×1.5, the other axes ×1 (the Docs/showcase axis is
scored by the [recruiter rubric](senior-recruiter.md) and enters the overall weighted
scorecard, not this lens). Anchors are taken from the research baseline evidence and
targets; intermediate scores interpolate.

| Axis | ≈ 70 (baseline-like) | 95+ (target) |
|---|---|---|
| Code quality | minimal lint selection; functions with CC far above 10; prompt inline without version; external format parsing in the domain | target Ruff selection with only shrinking per-file ignores; no C901 exceptions in `app/`; versioned prompts with hash; domain free of portfolio-format knowledge |
| Architecture | six layers enforced, but strict typing only in inner layers, mixed sync/async persistence and guard exceptions for entrypoints | six layers kept; extended guard (adapter independence, per-layer third-party allowlist, `ai` without drivers); mypy strict across `app/` at 0 errors; 0 `to_thread` in adapters; ADRs 009–015 accepted |
| Tests | many fast tests and real services in CI, but no coverage gate, no property or mutation testing, flat layout | layout by type; combined branch coverage ≥ 92% with gate and diff coverage ≥ 95%; ≥ 12 Hypothesis properties + stateful run lifecycle; mutation domain ≥ 85%, application ≥ 75%, ai ≥ 70% |
| Eval quality | strong question bank but no qrels, no Recall@k/nDCG, no validated judge | ≥ 150 bilingual qrels; Recall@5 ≥ 0.95, nDCG@5 ≥ 0.85, EN–ES gap ≤ 3 pp; judge κ ≥ 0.70, TPR/TNR ≥ 0.90; regression 100% on PRs; live capability results (P6) |
| Security | solid application controls; GitHub-native scanning off; no SAST, SBOM or attestation; open vendor findings | secret scanning + push protection on; CodeQL 0 high; dependency review and lockfile scanning on PRs; SBOM + provenance verifiable with `gh attestation verify`; tiered policy with VEX and SLA; 0 critical red-team findings |
| Perf / latency / cost | atomic cost controls and timeouts, but no load test and no written SLOs | written SLOs met: retrieval p95 ≤ 300 ms hybrid / ≤ 500 ms graph; overhead p95 ≤ 150 ms; 20-stream load without leaks; live TTFT p95 ≤ 3 s and cost p95 ≤ USD 0.005 (P6) |
| Observability | private metrics and opt-in OTLP, no GenAI semconv or version attributes | OTel GenAI semconv; `prompt_version`/`corpus_version` as low-cardinality attributes; run_id↔trace correlation; versioned dashboards/SLOs; still no transcripts |
| CI reliability | pinned, gated, ~4 min, but duplicated setup and no reporting | build-once job graph; PR wall p95 ≤ 4 min with more coverage; junit/coverage summaries; nightly flake detection without reruns in the gate |
| DX | keyless demo works but needs 8 commands and port choices | one-command fixture demo with ephemeral ports; task runner, pre-commit and devcontainer; consistent tool versions |

Automatic caps:

- Any failing required check on the reviewed commit caps the lens at 70.
- A v1 contract breaking change without the `contract-major` path caps Architecture at
  60.
- A committed secret or private material caps Security at 40.
