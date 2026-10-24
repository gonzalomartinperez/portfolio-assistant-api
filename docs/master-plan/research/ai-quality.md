# Research: AI quality plan

Planning research only. Every live or paid step below requires the owner's explicit
authorization and a spend cap (see [master plan](../README.md#owner-requirements)).

## Retrieval: dataset and metrics

- **Bilingual qrels:** ≥ 150 queries (≥ 75 EN, ≥ 75 ES) in
  `evals/retrieval/queries.jsonl` + `evals/retrieval/qrels.jsonl` (chunk_id → relevance
  0/1/2), derived from the 100 families of the bank (do not invent new ones), stratified
  by `kind` (direct, relationship, multi-hop, temporal, metric, education,
  unanswerable). Human labelling by the owner with a one-page guide; a double pass on
  20% to measure consistency.
- **Stable chunk identity** tied to `(commit, path, start_line, end_line)`, which
  already exists; qrels are re-mapped automatically when the corpus changes or are
  marked as stale.
- **Metrics:** Recall@5, nDCG@5, MRR@10, Hit@1 and "evidence sufficiency" (all pieces
  required for multi-hop in the top 5). Report by locale × kind × strategy
  (vector/lexical/graph/hybrid). Library: `ranx` (MIT) [source].
- **Frozen snapshot of real embeddings:** embed once (with explicit authorization) the
  pinned corpus + the eval queries with `text-embedding-3-small` and commit the snapshot
  (`evals/retrieval/embeddings-<corpus_sha>.npz`, 100% public content). Estimated cost
  < USD 0.01 [hypothesis: ~76 chunks + 150 queries ≪ 1 M tokens at USD 0.02/M]. CI
  measures real semantic recall **without network**. Re-snapshot only when the corpus
  or model changes.
- **Targets:** Recall@5 ≥ 0.95 and nDCG@5 ≥ 0.85 on the answerable holdout; **EN–ES
  gap ≤ 3 pp**; unanswerable: 0 citations in ≥ 98%.

## Weak spot in English: hypotheses and experiments

| Hypothesis | Experiment | Candidate change |
|---|---|---|
| H1 `simple` without stemming misses EN plurals/inflections ("projects", "worked") | Measure lexical Recall@5 per locale before/after | Generated columns per language: `to_tsvector('english', …)` for `en` chunks, `'spanish'` + `unaccent` for `es`, chosen by the chunk's `locale`; query with the same configuration (additive migration 010) |
| H2 RRF k=10 overweights rank 1 of a single signal | Sweep k ∈ {10, 30, 60} | k=60 (standard value from Cormack et al.), parameterizable |
| H3 chunks without context (TS fragments) embed poorly | Ablation with a contextual header (doc title + section + entity) prepended to the embedded text | "Contextual chunk headers" [source: Anthropic contextual retrieval] |
| H4 EN queries in sessions with ES history (or the reverse) retrieve only from the wrong locale | Cross-locale cases in qrels | Cross-locale retrieval with dedupe by `fact_id` |
| H5 keyword boosts mask the semantic ranking | Rule-by-rule ablation (A1 makes it possible) | Delete rules without a measurable contribution |

A reranker (local cross-encoder or API) **only if**, after H1–H5, Recall@5 < 0.95: the
corpus is ~76 chunks and the VPS is shared; a ~500 MB local model is not justified
without evidence.

## GraphRAG

- A specific suite of relational/multi-hop questions (≥ 40 of the 150) with qrels for
  *paths* (entity→relation→document) in addition to chunks.
- Measure the graph's marginal contribution: Recall@5(hybrid) − Recall@5(hybrid without
  graph) per kind. If the contribution is ≈ 0 outside multi-hop, restrict graph queries
  to relational intents (this already happens partially) and document it with numbers.

## Generation: suites and graders

| Suite | Content | Grader | When | Gate |
|---|---|---|---|---|
| **Regression** (deterministic) | 60 cases: citations, abstention, language, continuity, privacy; **recorded** answers (provider cassettes) | code (asserts over SSE events, citation mapping, language with Lingua) | every PR | 100% |
| **Capability** (live) | holdout 330 + multi-turn 15 + voice | calibrated judge + code checks + 10% human sample | manual / weekly, with a USD cap | trend; does not drop > 2 pp vs. baseline |
| **Safety / red team** | 40 adversarial + OWASP LLM Top 10 2025 plugins (direct and indirect prompt injection through the corpus, prompt extraction, PII, role jailbreak) | promptfoo + code asserts | fixture on PR (subset), live monthly | 0 critical |
| **Language** | unambiguous EN/ES + mixed + unsupported cases | Lingua + code | every PR (fixture) / live | ≥ 99% |

Terminology and lifecycle: capability evals that reach ~100% "graduate" to regression
[source: Anthropic, *Demystifying evals for AI agents*, 2026]. Report pass^k (k=3) for
capability, for consistency from the visitor's point of view.

## LLM-as-judge validated against humans

1. Binary criteria per dimension (no 1–10 scales): *faithful* (every claim supported by
   a citation), *citation_support*, *answers_question*, *abstains_correctly*,
   *tone_ok*.
2. Calibration dataset: ≥ 120 real answers (from the already-authorized live
   evaluations, anonymized and public by construction) labelled by the owner; 40% with
   failures.
3. Dev/test split of the calibration set; iterate the judge prompt only on dev.
4. Acceptance: TPR and TNR ≥ 0.90 on the *fail* class, Cohen's κ ≥ 0.70 per criterion
   on test. Recalibrate when the judge model or prompt changes [source: Shankar et al.,
   *Who Validates the Validators?*; Husain, evals FAQ 2025].
5. Judge pinned by version (`judge_prompt_version`, `judge_model`), minimal temperature,
   JSON answer with a short reason; prefer a model different from the generator when
   there is an option within the permitted provider.

## Prompt and version management

- `PromptSpec` (A3) + `prompt_version` in the database and reports; every PR that
  touches `app/ai/prompts/**` requires the `eval-required` label, which triggers (with
  environment approval) the capability suite in **sample 30** mode with a USD 0.50 cap
  and publishes the metrics diff as a comment.
- A prompt changelog inside `docs/explanation/prompts.md` with motivation and results.

## Cost and latency budgets (proposed SLOs)

| Metric | Target | Measurement |
|---|---|---|
| Retrieval p95 (in-process, local) | ≤ 300 ms (hybrid); graph ≤ 500 ms | Locust + `phase()` |
| API overhead until first delta (excludes provider) | p95 ≤ 150 ms | fixture provider with simulated latency |
| End-to-end live TTFT | p50 ≤ 1.5 s, p95 ≤ 3 s | capability suite |
| Full live answer | p95 ≤ 12 s; hard timeout 60 s (exists) | capability suite |
| Cost per answer | p95 ≤ USD 0.005; average reported per suite | ledger + report |
| Monthly cap | USD 10 (exists, validated in configuration) | ledger |

Baseline reference [measured in artifact]: fixture retrieval p50 ~280 ms hybrid and
**824 ms graph**.

## Offline vs online and tooling

- **Offline** (default, CI): everything above with fixture + cassettes + embeddings
  snapshot.
- **Online** (requires activation): private ratings already exist (default-off); add
  scheduled synthetic canaries (5 questions/day with a USD 0.05 cap) to detect provider
  drift; never export transcripts (the policy is kept).
- **Tooling:** the in-house harness (already exists, `scripts/evaluate_*`) as the source
  of truth + `ranx` for IR + `promptfoo` (MIT; acquired by OpenAI in Mar-2026, still
  open source) for red teaming. LLM observability: emit OTel GenAI semconv; if a UI is
  wanted, **self-hosted Langfuse** (MIT; part of ClickHouse since Jan-2026) or Arize
  Phoenix (Elastic License 2.0, to be reviewed). LangSmith stays as an optional manual
  exporter (already implemented). Do not add automatic tracing.
- **Neo4j decision (ADR-017):** a one-day spike with a `graph_edges` table in Postgres +
  a recursive CTE over the same entity projection (140 nodes, 502 edges [read]). If the
  GraphRAG suite stays within −1 pp and p95 ≤ the current one, option B (no Neo4j)
  removes the JVM, 1,261 image findings and a CI service; option A (keep) preserves the
  "Neo4j GraphRAG" showcase signal but requires migrating to the current CalVer line
  (5.26 is LTS with hotfixes until 2028 according to Neo4j, but the Jackson findings
  persist in the vendor image). Recommendation: decide with data; if Neo4j is kept,
  document the *why* in the README.
