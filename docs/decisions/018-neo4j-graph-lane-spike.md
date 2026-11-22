# ADR018: Neo4j graph lane fails the keep threshold; retire it after one confirmation run

Status: accepted (2026-11-22, master plan task M6-2; decision PAA-D12, DR-10). The decision is
the PAA-D12 spike rule applied to measured numbers. Its execution waits for the confirmation run
described below.

## Context and problem

Retrieval fuses lexical, vector and graph candidates ([ADR015](015-retrieval-pipeline-rrf-ablation.md)).
The graph lane reads a rebuildable Neo4j projection of the approved public corpus
([graph retrieval](../explanation/graph-retrieval.md)). That lane costs one extra container, a privileged
credential (Neo4j Community has no reader roles), a second backup target and its own vendor advisories.
PAA-D12 resolves the question with a measured rule: **keep Neo4j only if the graph lane adds at least
5 points of Recall@5 on multi-hop questions**. DR-10 pins Neo4j 5.26 LTS until that rule decides.

## Decision drivers

- Retrieval quality on the frozen corpus, measured per question kind, not intuition.
- Fewer moving parts on the VPS (OD-04 pragmatism, OD-60 hardening).
- No change to public behavior before the golden gate can prove it (golden replay waits for cassettes).

## Measurement

The retrieval harness runs in CI's `Database tests` job against real PostgreSQL 18 and Neo4j 5.26. It scores
every strategy on 131 resolved queries and reports `graph_marginal` (hybrid minus hybrid without graph).

- Evidence: CI [run 44983704753](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/44983704753),
  artifact `retrieval-report`, `develop` commit `5c6d711` (2026-11-22), corpus snapshot `1acbe54`.
- Regime: fixture hash embeddings, so `corpus.semantic` is false; no model calls.

Recall@5 by strategy and question kind:

| Kind | n | hybrid | hybrid without graph | graph alone | lexical | vector |
|---|---:|---:|---:|---:|---:|---:|
| direct | 69 | 0.7512 | 0.7585 | 0.3164 | 0.7512 | 0.5290 |
| education | 13 | 0.8718 | 0.8718 | 0.0000 | 0.8974 | 0.5256 |
| metric | 16 | 0.7188 | 0.7188 | 0.2500 | 0.8438 | 0.5000 |
| multi-hop | 24 | 0.9375 | 0.9792 | 0.8750 | 0.9792 | 0.5208 |
| relationship | 5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8000 |
| temporal | 4 | 1.0000 | 1.0000 | 0.5000 | 1.0000 | 0.7500 |
| **overall** | 131 | 0.8104 | 0.8219 | 0.4109 | 0.8359 | 0.5407 |

Graph marginal (hybrid minus hybrid without graph):

| Kind | Recall@5 | nDCG@5 |
|---|---:|---:|
| multi-hop | **-0.0417** | -0.0200 |
| direct | -0.0072 | -0.0035 |
| education, metric, relationship, temporal | 0.0000 | 0.0000 |
| overall | -0.0115 | -0.0055 |

On multi-hop questions the graph lane costs 4.2 points instead of adding the required 5. Two multi-hop
comparison queries (`rq-021` in English, `rq-076` cross-lingual) and one direct query (`rq-143`) drop from
1.0 to 0.5 Recall@5 when the graph lane is on; no query improves. The graph's own
candidates are good on multi-hop (0.875 alone), but the lexical lane already finds the same evidence (0.979),
so fusion likely spends top-5 slots on graph duplicates (a hypothesis: the report holds
metrics, not ranked lists).

The evidence is thin: one multi-hop query is worth 4.2 points at n = 24, so the result is two queries
losing half their recall and the +5 bar is about 1.2 queries. That is within noise, which is why execution
waits for the confirmation run below.

## Considered options

1. **Keep Neo4j.** Rejected by the rule, pending confirmation: the marginal is negative on every kind where it is not zero.
2. **Move the graph to PostgreSQL** (relationship table and recursive CTE). It removes the container, but
   it keeps a lane that adds no recall. Worth doing only if a later measurement shows a gain.
3. **Retire the graph lane and Neo4j.** Hybrid becomes lexical plus vector with the same rules and fusion.

## Decision

Option 3. The graph lane and the Neo4j dependency are retired. PostgreSQL stays the only store.

The execution is gated by one confirmation run, because this measurement uses hash embeddings. With real
embeddings the vector lane changes, and fusion with it could change the graph marginal:

1. **Confirm.** Re-run the harness on the real-embedding snapshot (M2-16). DR-04 covers its cost (USD 0.05),
   but it is a paid call, which repository agents never run (AGENTS.md), so it waits for an owner-run
   `eval-live` job.
   If multi-hop Recall@5 gains at least 5 points there, write a new ADR that supersedes this one and keeps
   the lane. Otherwise go to step 2.
2. **Expand.** Add a configuration switch that turns the graph lane off. The default stays on until the
   golden gate (cassette replay, 100%) passes with it off.
3. **Contract.** Default off, then remove the Neo4j adapter, the indexer projection, the graph check in
   readiness and the Compose service. That last step changes the production composition, so vps-ops does it in its
   own repository. It is scheduled after M7 so that the release does not change topology.

Until then Neo4j 5.26 LTS stays pinned and nothing about runtime behavior changes.

## Consequences

- Good: one container, one credential and one backup target fewer on the VPS once executed.
- Good: the number is in CI on every database run, so the confirmation step costs nothing extra to read.
- Bad: the confirmation needs the paid embedding snapshot, so the retirement cannot start before the owner
  runs it.
- Neutral: `graph_marginal` stays in the retrieval report as the standing check. If it ever turns positive
  on multi-hop by 5 points or more, this ADR is reopened.

## More information

- PAA-D12 in [the master plan README](../master-plan/README.md); DR-10 in
  [owner decisions](../master-plan/owner-decisions.md).
- Harness: `evals/harness/retrieval.py` (`graph_marginal`, strategy `hybrid_no_graph`).
