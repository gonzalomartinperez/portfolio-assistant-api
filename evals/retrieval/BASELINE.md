# Retrieval baseline (M2-5)

Source: CI run 43629194522 on `feat/m2-retrieval-harness`, corpus snapshot commit
`1acbe54906c88398652aebb8eae0c217fd0d8821`, mode: fixture embeddings; real PostgreSQL and Neo4j; no model calls. Qrels: `resolved` (two independent
labellers plus a resolver, see `evals/retrieval/LABELLING.md`). 152 queries, 131 with at
least one relevant key (21 no-answer queries are excluded from the averages).

The semantic lane (frozen real-embedding snapshot, M2-16) is parked: producing it is a paid
call. Vector numbers below use the fixture hash embeddings, so they measure plumbing, not
semantic recall.

| Strategy | Recall@5 | nDCG@5 | MRR@10 | Hit@1 | EN−ES gap (R@5) | Cross-lingual R@5 |
|---|---|---|---|---|---|---|
| graph | 0.411 | 0.459 | 0.519 | 0.519 | +0.032 | 0.506 |
| hybrid | 0.810 | 0.867 | 0.944 | 0.931 | -0.033 | 0.772 |
| hybrid_no_graph | 0.822 | 0.872 | 0.944 | 0.931 | -0.013 | 0.789 |
| lexical | 0.836 | 0.870 | 0.927 | 0.901 | -0.010 | 0.822 |
| vector | 0.541 | 0.547 | 0.637 | 0.588 | -0.191 | 0.189 |

Hybrid (the production strategy) by family:

| Family | n | Recall@5 |
|---|---|---|
| abstain | 2 | 1.000 |
| answerable_core | 96 | 0.757 |
| graph_multihop | 27 | 0.944 |
| tool_use | 6 | 1.000 |

## Findings

- Hybrid Recall@5 is 0.810, below the 0.90 target; lexical alone (0.836) beats hybrid in the fixture lane, and the graph marginal contribution (hybrid minus hybrid without graph) is -0.0115 Recall@5. Both feed the H1 to H5 ablations and the Neo4j decision (PAA-D12); they are fixture-lane numbers until the semantic lane exists.
- EN−ES gap on hybrid is -0.033 (paired -0.037): 3.3 pp, slightly above the 3 pp target, with Spanish ahead of English. The vector lane gap (-0.191) reflects the fixture hash embeddings, not the production model.
- Abstention experiment (hybrid, lexical-score proxy): no threshold removes spurious evidence without losing answerable Recall@5 (best harmless threshold 0, 0 spurious sources removed; 10 of 21 no-answer queries return evidence at threshold 0). A score threshold is not a viable abstention signal on this corpus; `evidence_sufficient` needs a different signal (follow-up).

## Ablations H1 to H5

| Id | Status | Note |
|---|---|---|
| graph | measured | hybrid_no_graph strategy; marginal contribution = hybrid minus hybrid_no_graph |
| h1 | not implementable without app change | follow-up: make the config a KnowledgeIndex parameter, then compare english/spanish with unaccent |
| h2 | not implementable without app change | follow-up: extract fusion into a function with k as an injected parameter (master plan file-moves: ai/retrieval/fusion.py), then run k in {10, 30, 60} |
| h3 | not implementable without app change | follow-up: contextual chunk headers need an indexing option and a re-index of the frozen snapshot |
| h4 | not implementable without app change | follow-up: cross-locale candidates with dedupe by fact; qrels here treat the other locale as not relevant by design (LABELLING.md) |
| h5 | not implementable without app change | follow-up: declarative rules (rules.toml) make each boost removable; until then hybrid minus vector/lexical only bounds their joint effect |

## Gate

`python -m evals.harness.retrieval --compare` runs a paired ranx test of hybrid against this
file on the answerable_core, graph_multihop and tool_use families and fails on a significant
(p < 0.05) Recall@5 drop. The CI database job runs it with `--compare` on every run that
includes the database profile. Refresh this file with `--write-baseline` only in a PR that
explains the change (a lower baseline needs a reason).
