# M1-2: P0-2 and P0-3 reproduced in CI conditions (2026-11-14)

Master plan roadmap M1-2. Method: the throwaway draft PR #149 (closed, not merged)
pointed the CI integration fixture at the current public portfolio commit
`c01e3ec1ce1a74e58c3a5f074f7b114b331e477e` (`content/` layout) instead of the pinned
`1acbe54` (`src/content/` layout). It ran on top of the M1-1 canonical-key branch
(#148). Fixture embeddings, real PostgreSQL 18 + pgvector and Neo4j 5.26 services,
no model calls. Run:
[43549618795](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/43549618795)
("Database tests": 9 failed, 39 passed).

## Results

| Finding | Result in CI conditions | Disposition |
|---|---|---|
| P0-1 (stale expected paths) | Fixed by M1-1 for `evals/retrieval.json`. The repro run found 7 more integration assertions in `tests/test_quality.py` that compared raw `src/content/...` paths | Converted to canonical keys in this PR (ADR012), with the same expected evidence. Nothing is loosened |
| P0-2 (`unsupported-employer` gets evidence) | **Reproduced.** Hybrid retrieval returns rows for "Did Gonzalo work at Google?" on the current corpus, with identical outcomes on both content roots. It passes on the pinned corpus | Issue [#152](https://github.com/gonzalomartinperez/portfolio-assistant-api/issues/152). First golden abstention item at M2-4; abstention experiment at M2-5. CI keeps the pinned corpus until the frozen snapshot (M2-2) |
| P0-3 (Neo4j vendor-reporting settings) | **Not reproduced.** `test_neo4j_effective_vendor_reporting_settings_are_disabled` passes in CI (not among the failures above, and green on every `develop` run). CI and `infra/compose/local.yaml` both set `NEO4J_dbms_usage__report_enabled=false` and `NEO4J_server_bolt_telemetry_enabled=false` | Closed. The audit fixture started Neo4j without these settings. The test is kept unchanged: it correctly rejects a fixture that reports usage |

All 9 failures of the repro run, by cause:

| Test | Cause |
|---|---|
| `test_knowledge.py::test_hybrid_retrieval_evaluation_and_relationship_provenance` | P0-2 (`unsupported-employer`) |
| `test_retrieval_layouts_integration.py::test_retrieval_cases_are_layout_neutral` | P0-2. Both layouts agree; the all-cases-pass assertion fails on the same case |
| `test_quality.py::test_reviewed_direct_questions` (5 parameters) | Raw `src/content` path comparison (P0-1 class), fixed here |
| `test_quality.py::test_unknown_question_has_no_evidence_and_graph_is_bounded` | Raw path comparison, fixed here |
| `test_quality.py::test_graph_outage_falls_back_to_verified_text` | Raw path comparison, fixed here |

On the pinned corpus, which is the CI default, the integration lane is green.
