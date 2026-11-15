"""Run the retrieval harness on the real stores (CI database job)."""

import json
import os
from pathlib import Path

import pytest

from evals.harness.retrieval import (
    STRATEGIES,
    load_qrels,
    load_queries,
    real_retriever,
    run_harness,
    write_json,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TEST_INTEGRATION") != "1",
        reason="requires isolated PostgreSQL and Neo4j fixtures",
    ),
]


def test_harness_runs_all_strategies_on_the_real_stores():
    pytest.importorskip("ranx")
    queries = load_queries()
    qrels, source = load_qrels()
    with real_retriever() as retrieve:
        report = run_harness(queries, qrels, source, retrieve)
    write_json(Path("artifacts/retrieval-report-integration.json"), report)
    assert set(report["strategies"]) == set(STRATEGIES)
    assert report["queries"]["scored"] == len(qrels)
    for data in report["strategies"].values():
        assert data["overall"]["n"] == len(qrels)
        assert 0.0 <= data["overall"]["recall@5"] <= 1.0
    assert report["strategies"]["hybrid"]["overall"]["recall@5"] > 0
    assert report["abstention"]["hybrid"]["sweep"]
    json.dumps(report)
