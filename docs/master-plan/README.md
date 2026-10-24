# Master plan 2026-10 (planning only)

> **Status: planning documentation. Nothing in this folder is scheduled, authorized or
> being executed.** Work starts only when the owner, Gonzalo Martin Perez, decides to
> start a phase. This plan does not change [AGENTS.md](../../AGENTS.md),
> [CONTRIBUTING.md](../../CONTRIBUTING.md) or any current policy; it does not authorize
> merges, main promotion, image publication, paid calls or deployment.

| File | Contents |
|---|---|
| [roadmap.md](roadmap.md) | Phases P0–P6 with scope, acceptance criteria, effort, risks and activation gates |
| [scorecard.md](scorecard.md) | Axes, baselines, targets, expected score by phase and automated measurement |
| [rubrics/](rubrics/) | Fixed senior developer, senior designer and senior recruiter rubrics |
| [research/](research/) | Baseline audit, target architecture, AI quality, testing, CI/CD and supply chain, standards/docs/skills, dependencies, sources |
| [ecosystem.md](ecosystem.md) | Pointer to the cross-repository plan in the portfolio repository |

## Rationale

The repository is far more rigorous than the average portfolio project: six layers with
an AST guard, 866 tests, real services in CI, versioned contracts, atomic cost budgets,
a threat model and dated evidence. The audited weighted baseline is **72/100**. What
separates it from 95+ is not a lack of work but three gaps:

1. **Measurable AI quality.** Retrieval has 9 binary cases, no qrels and no Recall@k;
   there is no validated judge and no human labels; CI embeddings are a 64-dimension
   hash, so real semantic recall is never measured. English lexical recall is weak
   (`'simple'` text-search configuration without stemming).
2. **Concentrated complexity.** `PublicRetrieval.search` has cyclomatic complexity 48
   with hardcoded keywords, TS-syntax regexes and path boosts; the domain parses the
   portfolio's TS format; prompts are unversioned strings.
3. **Showcase readability.** Caveats precede value in the README, 46 dated reports have
   no hierarchy, and there is no results table, CHANGELOG or release.

Supply-chain hygiene in a public repository (secret scanning and push protection off, no
CodeQL, no SBOM/attestation, open Neo4j vendor findings) is the fastest independent
win. Details: [baseline audit](research/audit-baseline.md).

## Method

- Source audited: `origin/develop` at `44ae6c7` (merge of PR #123), 2026-10-24.
- Read-only: `git archive` export to a temporary directory, `uv sync --frozen`, offline
  commands only, no API keys and no paid calls. The local checkout was not touched.
  The audit machine used uv 0.12.10 while the repository requires 0.13.1; the
  dependency sync still succeeded.
- Evidence is labelled **[measured]** (command output or count), **[read]** (code or
  docs), **[hypothesis]** (must be measured before acting) or **[source]** (cited
  external practice; full list in [sources](research/sources.md)).
- Scores per axis are expert judgement anchored to that evidence; the weighted score
  uses ×1.5 for AI (eval) quality and architecture and ×1 for the rest.
- This folder is a faithful English consolidation of the owner's Spanish planning
  research of 2026-10-24. Rubric point allocations and activation gates are the only
  additions; they encode the owner requirements below.

## Owner requirements

- **Planning only until the owner decides.** No phase, ADR, dependency or setting
  change proceeds from this document alone.
- **95+ on every axis**, evaluated through three lenses with fixed rubrics: senior
  developer, senior designer (API/streaming UX) and senior recruiter (public showcase).
  See [rubrics](rubrics/) and [scorecard](scorecard.md).
- **Any justified library is allowed.** Justification means purpose, cost, license and
  health, as in [dependencies](research/dependencies.md), plus the repository's
  [dependency policy](../dependency-updates.md).
- **VPS-gated activation.** The VPS is not purchased yet. Production activation, online
  canaries against a deployed service, self-hosted observability UIs and
  VPS-representative load numbers wait for it; vps-ops keeps deployment ownership.
- **Paid live evals need explicit authorization and a spend cap** for each run or
  campaign, including the one-off embeddings snapshot.

## Decisions, reasons and sources

| Decision | Reason | Source |
|---|---|---|
| Keep the six layers, the AST guard and `Protocol` ports; no DI framework | The guard detects dynamic imports (better than import-linter for "domain stdlib-only"); structural typing keeps ports light | [architecture](research/architecture.md#what-is-kept-do-not-touch); Cosmic Python; PEP 544; import-linter |
| Split retrieval into a declarative pipeline with standard RRF (k=60, parameterizable) and TOML rules | CC 48 → ≤ 10; each rule measurable by ablation; removes overfitting | A1; Cormack et al. 2009 |
| Move portfolio-format parsing out of the domain | A truly pure domain; robust to portfolio layout changes | A2 |
| Version prompts (`PromptSpec` with sha256) and record `prompt_version` | Prompt→quality traceability and per-PR eval diffs | A3 |
| Measure retrieval with ≥ 150 bilingual qrels and a frozen real-embeddings snapshot | Real semantic recall in CI without network or paid calls; estimated < USD 0.01 one-off [hypothesis] | [AI quality](research/ai-quality.md); ranx |
| Per-language text search (`english`, `spanish` + `unaccent`) as the first English experiment | The two direct baseline failures are EN queries under the `simple` configuration | H1; PostgreSQL text search docs |
| Reranker only if Recall@5 < 0.95 after H1–H5 | ~76-chunk corpus and a shared VPS do not justify a ~500 MB model without evidence | AI quality |
| Binary-criteria LLM judge calibrated against ≥ 120 owner labels (κ ≥ 0.70, TPR/TNR ≥ 0.90) | An unvalidated judge produces unreliable numbers | Shankar et al. 2024; Husain 2025; Anthropic 2026 |
| Separate regression, capability, red-team and language suites; capability graduates to regression | Different cadence, cost and gate per suite | Anthropic 2026; OWASP LLM Top 10 2025; promptfoo |
| Additive error/SSE v1.1 (enum codes, `retryable`, `retry_after_s`, RFC 9457-style `type`, EN/ES messages, more progress phases) | Actionable error UX and perceived progress without breaking v1 | A6/A7; RFC 9457 |
| Hypothesis (incl. stateful run lifecycle) and mutmut 3.x on domain/application | Invariants (budget, sequence, single terminal) and test strength are not covered by example tests or coverage alone | [testing](research/testing.md); Hypothesis; mutmut |
| Locust instead of k6 for load | Same language and SSE support through an own client; k6 has no native SSE | Locust docs; Grafana community thread |
| Build-once CI, SBOM + provenance attestations, CodeQL, dependency review, osv/pip-audit, gitleaks, OpenVEX tiered policy | Supply-chain completeness for a public repository; aims at SLSA Build L2/L3 | [CI/CD](research/ci-cd-supply-chain.md); SLSA v1.1; OpenSSF Scorecard; OpenVEX |
| release-please + immutable releases; keep 0 required reviews but add CODEOWNERS | Single maintainer; Conventional Commits are already in use | release-please; GitHub immutable releases |
| Showcase README ≤ 250 lines with a measured-results table; Diátaxis; MADR 4.0 ADRs; C4 | Value before caveats; any decision within 2 clicks | [standards/docs/skills](research/standards-docs-skills.md); Diátaxis; MADR; C4 |
| Rejected: Pact, DeepEval/RAGAS as a gate, local cross-encoder, Phoenix | Overkill with 2 own consumers; uncalibrated LLM metrics; no evidence of need; ELv2 license | [dependencies](research/dependencies.md) |

## Open owner decisions

| Decision | Options | Recommendation (from the research) |
|---|---|---|
| When to start, and in which order | start P0 alone; or P0 + P1 together | Start with P0 (1–2 days, mostly settings); P1 before P2 so refactors have a metric safety net. |
| Neo4j (ADR-017) | A: keep and migrate to the current CalVer line; B: graph in Postgres (`graph_edges` + recursive CTE) | Decide with data from a one-day spike: choose B if the GraphRAG suite stays within −1 pp and p95 ≤ current; if Neo4j is kept, document why in the README. |
| `src/` layout (A9, ADR-015) | migrate in one mechanical PR; do not migrate | Optional, high churn: either an isolated mechanical PR or not at all. |
| Embeddings snapshot spend | authorize a one-off run with a cap; postpone | Authorize when P1 starts; estimated < USD 0.01 [hypothesis]; set an explicit cap. |
| Live capability suite and red team (P6) | owner-defined USD cap per campaign; postpone | Required for 95+ Eval quality; define the cap when the VPS timeline is known. |
| `eval-required` PR samples | sample 30 with a USD 0.50 cap; manual only | Use the research default (sample 30, USD 0.50 cap) behind environment approval. |
| Daily synthetic canaries | 5 questions/day with a USD 0.05 cap; none | Only after the VPS and deployment exist. |
| LLM observability UI | none (OTel GenAI semconv only); self-hosted Langfuse; Arize Phoenix | Emit semconv first; Langfuse (MIT) only if a UI is wanted and the VPS has room; Phoenix rejected (ELv2). |
| Labelling time | owner labels qrels (≥ 150) and judge set (≥ 120) | Needed for P1 acceptance; a 20% double pass measures consistency. |
| Repository settings | owner enables secret scanning, push protection, CodeQL, immutable releases, homepage | Enable in P0; they cost nothing on a public repository. |
| Image publication and attestations | publish to GHCR on release; keep local only | Only with explicit approval; publication is not deployment. |
| Rubric point allocations | accept v1; adjust | Adjust, if at all, before the first scored review, then freeze. |

## Limits

- The baseline reflects one commit (`44ae6c7`) on 2026-10-24; later commits may change
  any number.
- Axis scores are expert judgement, not mechanical outputs; the designer and recruiter
  lenses have qualitative findings but no numeric baseline until the first scored review.
- Cost figures marked [hypothesis] are estimates; tool facts (versions, licenses,
  acquisitions) reflect the research date and must be rechecked at adoption.
- Phase score expectations are forecasts. Without P6 (paid live evaluation, and the VPS
  for online parts), Eval quality is expected to top out at ~90 and Observability at
  94, so the owner's 95+-on-every-axis goal is not reachable without those gates.
- No live, VPS or production verification was performed for this plan.
