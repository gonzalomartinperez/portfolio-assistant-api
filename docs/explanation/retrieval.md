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

| Variant | Recall@5 delta (95% CI, p-value) | nDCG@5 delta (95% CI, p-value) |
|---|---|---|
| All rule variants and `hybrid_rrf60` | pending first CI ablation run | pending first CI ablation run |
