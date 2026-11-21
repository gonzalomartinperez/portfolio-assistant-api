# Retrieval pipeline

Retrieval analyzes the question, selects eligible public corpus chunks, ranks
lexical, vector and graph candidates, applies hybrid re-ranking, and returns up to
five cited sources. See [graph retrieval](graph-retrieval.md) for corpus provenance
and relationship traversal.

## Rule ablation

[The packaged rules](../../src/portfolio_assistant/ai/retrieval/rules.toml) define the default vocabulary
and weights. [ADR015](../decisions/015-retrieval-pipeline-rrf-ablation.md) records
how the pipeline handles disabled rules and when evidence supports removing one.

| Rule ID | What it does | Kind |
|---|---|---|
| `boost_spoken_languages` | Adds the `weights.spoken_languages` weight from `rules.toml` to profile chunks with spoken-language entries on language questions. | Boost |
| `boost_overview_profile_head` | Adds the `weights.overview_profile_head` weight from `rules.toml` to profile opening chunks for overview questions. | Boost |
| `boost_company_contributions` | Adds the `weights.company_contributions` weight from `rules.toml` to experience chunks with contributions for a company named in the question. | Boost |
| `multiplier_entity_path` | Multiplies the score by the `weights.entity_path_multiplier` weight from `rules.toml` for chunks in documents that declare an entity named in the question. | Boost |
| `overview_first` | Promotes profile opening chunks on overview questions. | Reorder |
| `affiliation_filter` | Keeps chunks that mention the requested affiliation and promotes matching company declarations. | Filter |
| `performance_metrics` | Promotes qualified metric entries on performance questions. | Reorder |
| `exact_name` | Promotes chunks whose declared name appears in the query. | Reorder |
| `qualification_anchor` | Prepends education opening chunks on qualification questions. | Anchor |
| `relationship_anchors` | Prepends the best chunk per compared subject or the latest role per company. | Anchor |
| `technical_topic_anchors` | Prepends the best eligible chunk for each recognized technical topic in the question. | Anchor |
| `goals_metrics_anchor` | Prepends the strongest documented design-goal match on goal and measurement questions. | Anchor |

The database CI job runs the harness with `--ablate` and uploads
`retrieval-report-ablation.json`. Each `hybrid_without:<rule_id>` variant disables
one rule. `hybrid_rrf60` changes only the fusion offset. The `rule_ablation` report key contains the mean
paired difference (hybrid minus variant), a 95% paired bootstrap interval, and a
paired p-value for each metric. The fixture hash embeddings measure retrieval on
the frozen test corpus.

First measurement: CI run 44947190508 (PR #210, commit `624e625`, 2026-11-21), 131 paired
queries, fixture hash embeddings (`corpus.semantic` false, so only the lexical lane weights are
exercised). A positive delta means the rule helps.

| Variant | Recall@5 delta (95% CI, p) | nDCG@5 delta (95% CI, p) |
|---|---|---|
| `hybrid_rrf60` | -0.0025 (-0.0140 to +0.0089, p=0.671) | +0.0021 (-0.0048 to +0.0106, p=0.597) |
| `hybrid_without:affiliation_filter` | -0.0115 (-0.0305 to +0.0038, p=0.181) | -0.0100 (-0.0236 to +0.0007, p=0.107) |
| `hybrid_without:boost_company_contributions` | +0.0000 (+0.0000 to +0.0000, p=1.000) | +0.0000 (+0.0000 to +0.0000, p=1.000) |
| `hybrid_without:boost_overview_profile_head` | +0.0000 (+0.0000 to +0.0000, p=1.000) | +0.0000 (+0.0000 to +0.0000, p=1.000) |
| `hybrid_without:boost_spoken_languages` | +0.0038 (+0.0000 to +0.0115, p=0.319) | +0.0058 (+0.0000 to +0.0174, p=0.319) |
| `hybrid_without:exact_name` | +0.0000 (+0.0000 to +0.0000, p=1.000) | +0.0056 (+0.0000 to +0.0141, p=0.158) |
| `hybrid_without:goals_metrics_anchor` | +0.0000 (+0.0000 to +0.0000, p=1.000) | +0.0000 (+0.0000 to +0.0000, p=1.000) |
| `hybrid_without:multiplier_entity_path` | -0.0140 (-0.0267 to -0.0025, p=0.027) | +0.0021 (-0.0080 to +0.0141, p=0.708) |
| `hybrid_without:overview_first` | +0.0000 (+0.0000 to +0.0000, p=1.000) | +0.0000 (+0.0000 to +0.0000, p=1.000) |
| `hybrid_without:performance_metrics` | +0.0000 (+0.0000 to +0.0000, p=1.000) | +0.0000 (+0.0000 to +0.0000, p=1.000) |
| `hybrid_without:qualification_anchor` | -0.0025 (-0.0076 to +0.0000, p=0.319) | +0.0068 (-0.0007 to +0.0177, p=0.190) |
| `hybrid_without:relationship_anchors` | +0.0000 (+0.0000 to +0.0000, p=1.000) | +0.0000 (+0.0000 to +0.0000, p=1.000) |
| `hybrid_without:technical_topic_anchors` | +0.0000 (+0.0000 to +0.0000, p=1.000) | +0.0000 (+0.0000 to +0.0000, p=1.000) |

Reading (ADR 015 deletion criterion): seven rules show no measurable effect on this query set
(delta exactly 0 on both metrics); that is absence of evidence, so none is deleted until the
golden and retrieval gates confirm with each removed. `multiplier_entity_path` has a negative
Recall@5 contribution (-0.0140, CI excludes 0, p 0.027) and is the first deletion candidate.
`affiliation_filter` also leans negative and `boost_spoken_languages` and `exact_name` lean
positive, but their intervals include 0; `qualification_anchor` is mixed. `hybrid_rrf60` is
indistinguishable from offset 10, so the default stays. Deleting or changing a rule is a
separate PR with the golden and retrieval gates as evidence.
