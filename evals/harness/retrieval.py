"""Retrieval harness: Recall@k, nDCG, MRR and Hit@1 with ranx over canonical evidence keys.

Runs the real retrieval path (PostgreSQL, Neo4j, fixture hash embeddings; no model call)
for the strategies vector, lexical, graph, hybrid and hybrid without graph, scores them
against ``evals/retrieval/qrels.jsonl`` (or, until labelling is finished, the PROPOSED
relevance in ``qrels.candidates.jsonl``, flagged in the report) and writes one JSON report.

``--write-baseline`` stores the report as ``evals/baselines/retrieval.json``;
``--compare`` runs a paired ranx significance test of the current run against that
baseline and exits non-zero on a significant (p < 0.05) Recall@5 drop on the golden-relevant
families (answerable_core, graph_multihop, tool_use). Pure functions (breakdown, gap,
abstention sweep, comparison decision) are separate from the I/O and unit tested offline.
``--ablate`` adds one run per disabled rule and an RRF offset 60 run, with paired deltas
against hybrid under ``rule_ablation``.

Usage: ``uv run --group eval python -m evals.harness.retrieval --out artifacts/retrieval-report.json``
"""

import argparse
import asyncio
import importlib
import json
import math
import random
import sys
import warnings
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.ai.retrieval.rules import DEFAULT_RULES, RULE_IDS
from app.domain.evidence import lexical_score, tokens
from app.domain.portfolio_paths import canonical_key

if TYPE_CHECKING:
    from app.ai.retrieval.rules import RetrievalRules

ROOT = Path(__file__).resolve().parents[2]
QUERIES = ROOT / "evals" / "retrieval" / "queries.jsonl"
QRELS = ROOT / "evals" / "retrieval" / "qrels.jsonl"
CANDIDATES = ROOT / "evals" / "retrieval" / "qrels.candidates.jsonl"
BASELINE = ROOT / "evals" / "baselines" / "retrieval.json"

SCHEMA_VERSION = "1"
MODE = "fixture embeddings; real PostgreSQL and Neo4j; no model calls"
STRATEGIES = ("vector", "lexical", "graph", "hybrid", "hybrid_no_graph")
WITHOUT_PREFIX = "hybrid_without:"
ABLATION_STRATEGIES = ("hybrid_rrf60", *(WITHOUT_PREFIX + rule for rule in sorted(RULE_IDS)))
ABLATION_METRICS = ("recall@5", "ndcg@5")
BOOTSTRAP_SEED = 42
BOOTSTRAP_SAMPLES = 2000
# Report metric name -> ranx metric. Recall@5 is primary: five sources reach the generator.
METRICS = {
    "recall@5": "recall@5",
    "ndcg@5": "ndcg@5",
    "mrr@10": "mrr@10",
    "hit@1": "hit_rate@1",
}
PRIMARY = "recall@5"
GATE_FAMILIES = ("answerable_core", "graph_multihop", "tool_use")
GATE_STRATEGIES = ("hybrid",)
ALPHA = 0.05
ABSTENTION_STRATEGIES = ("hybrid", "vector")
ABSTENTION_THRESHOLDS = (0, 1, 2, 3, 4, 6, 8, 10, 15, 20, 30)
EMPTY = "__empty__"

Query = dict[str, Any]
Qrels = dict[str, dict[str, int]]
Record = dict[str, Any]
Records = dict[str, Record]
PerQuery = dict[str, dict[str, float]]
Retriever = Callable[[str, str, str], Record]

# H1 to H5 (assistant-quality.md section 7), including follow-up experiments.
ABLATIONS: dict[str, dict[str, str]] = {
    "graph": {
        "status": "measured",
        "seam": "KnowledgeIndex port: relationships() replaced by an empty result",
        "note": "hybrid_no_graph strategy; marginal contribution = hybrid minus hybrid_no_graph",
    },
    "h1": {
        "status": "not implementable without app change",
        "seam": "none: the text search config is the literal simple in the candidates SQL "
        "(app/adapters/retrieval.py)",
        "note": "follow-up: make the config a KnowledgeIndex parameter, then compare "
        "english/spanish with unaccent",
    },
    "h2": {
        "status": "available with --ablate",
        "seam": "RetrievalRules.fusion_offset",
        "note": "hybrid_rrf60 compares offset 60 with the legacy offset 10 using the same weights",
    },
    "h3": {
        "status": "not implementable without app change",
        "seam": "none: chunk text is embedded as stored at indexing time",
        "note": "follow-up: contextual chunk headers need an indexing option and a re-index "
        "of the frozen snapshot",
    },
    "h4": {
        "status": "not implementable without app change",
        "seam": "none: the locale preference filter is inline in PublicRetrieval.search",
        "note": "follow-up: cross-locale candidates with dedupe by fact; qrels here treat the "
        "other locale as not relevant by design (LABELLING.md)",
    },
    "h5": {
        "status": "available with --ablate",
        "seam": "RetrievalRules.disabled",
        "note": "hybrid_without:<rule_id> measures each rule against hybrid",
    },
}


# --------------------------------------------------------------------------- data loading


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def load_queries(path: Path = QUERIES) -> list[Query]:
    queries = read_jsonl(path)
    ids = [q["id"] for q in queries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate query ids")
    return queries


def qrels_from_rows(rows: Sequence[dict[str, Any]], field: str) -> Qrels:
    qrels: Qrels = {}
    for row in rows:
        if row[field] > 0:
            qrels.setdefault(row["query_id"], {})[row["key"]] = int(row[field])
    return qrels


def load_qrels(qrels_path: Path = QRELS, candidates_path: Path = CANDIDATES) -> tuple[Qrels, str]:
    """Return ``(qrels, source)``; ``source`` is ``resolved`` or ``proposed``."""
    if qrels_path.exists():
        return qrels_from_rows(read_jsonl(qrels_path), "relevance"), "resolved"
    rows = [
        {"query_id": c["query_id"], "key": item["key"], "proposed": item["proposed"]}
        for c in read_jsonl(candidates_path)
        for item in c["candidates"]
    ]
    return qrels_from_rows(rows, "proposed"), "proposed"


# ------------------------------------------------------------------------ run assembly


def ranked_keys(record: Record) -> list[str]:
    """Distinct canonical keys in rank order (the first source of a key sets its rank)."""
    return list(dict.fromkeys(source["key"] for source in record["sources"]))


def runs_from_records(records: Records) -> dict[str, list[str]]:
    return {qid: ranked_keys(record) for qid, record in records.items()}


def recall_at(ranked: Sequence[str], relevant: Sequence[str], k: int = 5) -> float:
    if not relevant:
        raise ValueError("recall is undefined without relevant keys")
    return len(set(ranked[:k]) & set(relevant)) / len(relevant)


def ranx_run(runs: dict[str, list[str]], qids: Sequence[str], name: str) -> Any:
    ranx = importlib.import_module("ranx")
    data = {
        qid: ({key: 1.0 / (rank + 1) for rank, key in enumerate(runs.get(qid, []))} or {EMPTY: 0.0})
        for qid in qids
    }
    return ranx.Run.from_dict(data, name=name)


def score_run(runs: dict[str, list[str]], qrels: Qrels) -> PerQuery:
    """Per-query Recall@5, nDCG@5, MRR@10 and Hit@1 with ranx for the queries in qrels."""
    ranx = importlib.import_module("ranx")
    qids = sorted(qrels)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        run = ranx_run(runs, qids, "run")
        ranx.evaluate(ranx.Qrels.from_dict(qrels), run, list(METRICS.values()))
    return {
        qid: {name: float(run.scores[metric][qid]) for name, metric in METRICS.items()}
        for qid in qids
    }


# -------------------------------------------------------------------- pure aggregations


def finite(value: Any) -> Any:
    """Replace NaN (an empty group) with None so reports stay strict JSON."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {key: finite(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [finite(item) for item in value]
    return value


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def mean_metrics(per_query: PerQuery, qids: Sequence[str]) -> dict[str, Any]:
    chosen = [qid for qid in qids if qid in per_query]
    return {
        "n": len(chosen),
        **{name: round(mean([per_query[q][name] for q in chosen]), 4) for name in METRICS},
    }


def stratum_of(query: Query) -> str:
    return "cross_lingual" if query.get("cross_lingual") else "monolingual"


DIMENSIONS: dict[str, Callable[[Query], str]] = {
    "locale": lambda q: str(q["locale"]),
    "family": lambda q: str(q["family"]),
    "kind": lambda q: str(q["kind"]),
    "stratum": stratum_of,
}


def breakdown(
    per_query: PerQuery, queries: Sequence[Query], dimension: str
) -> dict[str, dict[str, Any]]:
    """Mean metrics per value of ``dimension`` over the scored (answerable) queries."""
    groups: dict[str, list[str]] = defaultdict(list)
    for query in queries:
        if query["id"] in per_query:
            groups[DIMENSIONS[dimension](query)].append(query["id"])
    return {value: mean_metrics(per_query, qids) for value, qids in sorted(groups.items())}


def locale_gap(
    per_query: PerQuery, queries: Sequence[Query], metric: str = PRIMARY
) -> dict[str, Any]:
    """EN minus ES on monolingual queries, overall and over EN/ES pairs (same intent)."""
    scored = [q for q in queries if q["id"] in per_query and not q.get("cross_lingual")]
    by_locale: dict[str, list[float]] = {"en": [], "es": []}
    pairs: dict[str, dict[str, float]] = defaultdict(dict)
    for query in scored:
        value = per_query[query["id"]][metric]
        by_locale[query["locale"]].append(value)
        pairs[query["pair_id"]][query["locale"]] = value
    both = [p for p in pairs.values() if "en" in p and "es" in p]
    return {
        "metric": metric,
        "en": round(mean(by_locale["en"]), 4),
        "es": round(mean(by_locale["es"]), 4),
        "gap": round(mean(by_locale["en"]) - mean(by_locale["es"]), 4),
        "n_en": len(by_locale["en"]),
        "n_es": len(by_locale["es"]),
        "paired_gap": round(mean([p["en"] - p["es"] for p in both]), 4) if both else None,
        "pairs": len(both),
    }


def graph_marginal(
    hybrid: PerQuery, no_graph: PerQuery, queries: Sequence[Query]
) -> dict[str, Any]:
    """Hybrid minus hybrid without graph, overall and per kind (Recall@5 and nDCG@5)."""
    kinds: dict[str, list[str]] = defaultdict(list)
    for query in queries:
        if query["id"] in hybrid and query["id"] in no_graph:
            kinds[query["kind"]].append(query["id"])

    def delta(qids: Sequence[str]) -> dict[str, Any]:
        return {
            "n": len(qids),
            **{
                name: round(
                    mean([hybrid[q][name] for q in qids]) - mean([no_graph[q][name] for q in qids]),
                    4,
                )
                for name in ("recall@5", "ndcg@5")
            },
        }

    everything = [q for qids in kinds.values() for q in qids]
    return {
        "overall": delta(everything) if everything else None,
        "by_kind": {kind: delta(qids) for kind, qids in sorted(kinds.items())},
    }


def abstention_sweep(
    records: Records,
    queries: Sequence[Query],
    qrels: Qrels,
    thresholds: Sequence[float] = ABSTENTION_THRESHOLDS,
) -> dict[str, Any]:
    """Would a lexical-score threshold drop spurious evidence without hurting Recall@5?

    A source survives at threshold T when its lexical score is at least T. For
    no-answer queries the spurious rate is the share still returning any source; for
    answerable queries it is the mean Recall@5 on the surviving sources. Report only: the
    app has no ``evidence_sufficient`` signal, so nothing here changes retrieval.
    """
    by_id = {q["id"]: q for q in queries}
    answerable = [qid for qid in qrels if qid in records]
    no_answer = [
        qid
        for qid, record in records.items()
        if qid in by_id and not by_id[qid].get("expects_evidence", True)
    ]
    employer = [qid for qid in no_answer if by_id[qid].get("class") == "unsupported_employer"]

    def survivors(qid: str, threshold: float) -> list[str]:
        kept = [s for s in records[qid]["sources"] if s["score"] >= threshold]
        return list(dict.fromkeys(s["key"] for s in kept))

    def recall(threshold: float) -> float:
        return mean([recall_at(survivors(qid, threshold), list(qrels[qid])) for qid in answerable])

    baseline = recall(0)
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        remaining = [qid for qid in no_answer if survivors(qid, threshold)]
        remaining_employer = [qid for qid in employer if survivors(qid, threshold)]
        current = recall(threshold)
        rows.append(
            {
                "threshold": threshold,
                "answerable_recall@5": round(current, 4),
                "recall_drop": round(baseline - current, 4),
                "no_answer_with_evidence": len(remaining),
                "no_answer_with_evidence_rate": round(len(remaining) / len(no_answer), 4)
                if no_answer
                else None,
                "unsupported_employer_with_evidence": len(remaining_employer),
            }
        )
    harmless = [r for r in rows if r["recall_drop"] <= 0]
    best = min(harmless, key=lambda r: (r["no_answer_with_evidence"], -r["threshold"]))
    return {
        "metric": "lexical_score proxy (app.domain.evidence.lexical_score) on returned sources",
        "answerable_queries": len(answerable),
        "no_answer_queries": len(no_answer),
        "unsupported_employer_queries": len(employer),
        "baseline_recall@5": round(baseline, 4),
        "sweep": rows,
        "best_threshold_without_recall_loss": best["threshold"],
        "spurious_removed_at_best": (
            next((r for r in rows if r["threshold"] == 0), rows[0])["no_answer_with_evidence"]
            - best["no_answer_with_evidence"]
        ),
    }


# ---------------------------------------------------------------------------- comparison


def decide_drop(
    baseline_mean: float, current_mean: float, p_value: float, alpha: float = ALPHA
) -> bool:
    """A significant drop: the mean fell and the paired test rejects equality at alpha."""
    if math.isnan(p_value) or math.isnan(baseline_mean) or math.isnan(current_mean):
        return False
    return current_mean < baseline_mean and p_value < alpha


def paired_p_value(
    qrels: Qrels,
    base: dict[str, list[str]],
    current: dict[str, list[str]],
    *,
    metric: str = PRIMARY,
) -> float:
    """Run a paired Student t-test via ranx, defaulting to the Recall@5 gate metric."""
    qids = sorted(qrels)
    if len(qids) < 2:
        return math.nan
    if metric == PRIMARY and all(
        recall_at(base.get(q, []), list(qrels[q])) == recall_at(current.get(q, []), list(qrels[q]))
        for q in qids
    ):
        return 1.0
    ranx = importlib.import_module("ranx")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        report = ranx.compare(
            ranx.Qrels.from_dict({q: qrels[q] for q in qids}),
            [ranx_run(base, qids, "baseline"), ranx_run(current, qids, "current")],
            metrics=[METRICS[metric]],
            stat_test="student",
            max_p=ALPHA,
        )
    return float(report.to_dict()["current"]["comparisons"]["baseline"][METRICS[metric]])


def compare_reports(
    baseline: dict[str, Any],
    current_runs: dict[str, dict[str, list[str]]],
    qrels: Qrels,
    queries: Sequence[Query],
    *,
    strategies: Sequence[str] = GATE_STRATEGIES,
    families: Sequence[str] = GATE_FAMILIES,
    alpha: float = ALPHA,
    p_value: Callable[..., float] = paired_p_value,
) -> dict[str, Any]:
    gate = {q["id"] for q in queries if q["family"] in families}
    results: dict[str, Any] = {}
    failed = False
    for strategy in strategies:
        base_runs = baseline["runs"].get(strategy)
        if base_runs is None or strategy not in current_runs:
            # A gated strategy that vanished must not pass the gate silently.
            results[strategy] = {"status": "missing in baseline or current run"}
            failed = True
            continue
        qids = sorted(q for q in qrels if q in gate and q in base_runs)
        subset = {q: qrels[q] for q in qids}
        base_mean = mean([recall_at(base_runs[q], list(subset[q])) for q in qids])
        cur_mean = mean(
            [recall_at(current_runs[strategy].get(q, []), list(subset[q])) for q in qids]
        )
        p = p_value(subset, base_runs, current_runs[strategy])
        drop = decide_drop(base_mean, cur_mean, p, alpha)
        failed |= drop
        results[strategy] = {
            "queries": len(qids),
            "baseline_recall@5": round(base_mean, 4),
            "current_recall@5": round(cur_mean, 4),
            "delta": round(cur_mean - base_mean, 4),
            "p_value": None if math.isnan(p) else round(p, 6),
            "alpha": alpha,
            "significant_drop": drop,
        }
    return {"families": list(families), "strategies": results, "failed": failed}


# ------------------------------------------------------------------------------ report


def assemble_report(
    queries: Sequence[Query],
    qrels: Qrels,
    qrels_source: str,
    records: dict[str, Records],
    per_query: dict[str, PerQuery],
    *,
    commit: str | None = None,
) -> dict[str, Any]:
    strategies: dict[str, Any] = {}
    for name, scores in per_query.items():
        strategies[name] = {
            "overall": mean_metrics(scores, sorted(scores)),
            "by_locale": breakdown(scores, queries, "locale"),
            "by_family": breakdown(scores, queries, "family"),
            "by_kind": breakdown(scores, queries, "kind"),
            "by_stratum": breakdown(scores, queries, "stratum"),
            "en_es_gap": locale_gap(scores, queries),
        }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mode": MODE,
        "commit_sha": commit,
        "qrels_source": qrels_source,
        "primary_metric": PRIMARY,
        "queries": {
            "total": len(queries),
            "scored": len(qrels),
            "no_answer": sum(1 for q in queries if not q.get("expects_evidence", True)),
            "by_locale": count_by(queries, "locale"),
            "by_kind": count_by(queries, "kind"),
            "by_family": count_by(queries, "family"),
            "cross_lingual": sum(1 for q in queries if q.get("cross_lingual")),
        },
        "strategies": strategies,
        "graph_marginal": graph_marginal(per_query["hybrid"], per_query["hybrid_no_graph"], queries)
        if {"hybrid", "hybrid_no_graph"} <= set(per_query)
        else None,
        "abstention": {
            name: abstention_sweep(records[name], queries, qrels)
            for name in ABSTENTION_STRATEGIES
            if name in records
        },
        "ablations": ABLATIONS,
        "runs": {name: runs_from_records(recs) for name, recs in records.items()},
        "sources": records,
        "per_query": per_query,
    }
    return report


def _paired_interval(deltas: list[float]) -> tuple[float, float]:
    if not deltas:
        return math.nan, math.nan
    rng = random.Random(BOOTSTRAP_SEED)  # noqa: S311, RUF100 - Seeded statistical resampling.
    samples = sorted(mean(rng.choices(deltas, k=len(deltas))) for _ in range(BOOTSTRAP_SAMPLES))
    return samples[BOOTSTRAP_SAMPLES // 40], samples[BOOTSTRAP_SAMPLES * 39 // 40 - 1]


def _ablation_delta(
    qrels: Qrels,
    runs: dict[str, dict[str, list[str]]],
    per_query: dict[str, PerQuery],
    strategy: str,
    metric: str,
) -> dict[str, Any]:
    deltas = [
        per_query["hybrid"][qid][metric] - per_query[strategy][qid][metric] for qid in sorted(qrels)
    ]
    interval = _paired_interval(deltas)
    p_value = (
        paired_p_value(qrels, runs["hybrid"], runs[strategy], metric=metric)
        if any(deltas)
        else 1.0
        if len(deltas) >= 2
        else math.nan
    )
    return {
        "n": len(deltas),
        "mean_delta": round(mean(deltas), 4),
        "ci95": [round(bound, 4) for bound in interval],
        "p_value": round(p_value, 6),
    }


def _ablation_report(report: dict[str, Any], qrels: Qrels) -> dict[str, Any]:
    return {
        "reference": "hybrid",
        "delta_direction": "hybrid minus variant",
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "strategies": {
            name: report["strategies"][name] for name in ("hybrid", *ABLATION_STRATEGIES)
        },
        "paired_deltas": {
            name: {
                metric: _ablation_delta(qrels, report["runs"], report["per_query"], name, metric)
                for metric in ABLATION_METRICS
            }
            for name in ABLATION_STRATEGIES
        },
    }


def count_by(queries: Sequence[Query], field: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for query in queries:
        counts[str(query[field])] += 1
    return dict(sorted(counts.items()))


# ----------------------------------------------------------------------------- real I/O


class _NoGraph:
    """Index port wrapper whose graph lane is empty: hybrid without graph."""

    def __init__(self, index: Any) -> None:
        self._index = index

    async def candidates(self, question: str) -> Any:
        return await self._index.candidates(question)

    async def relationships(self, *args: Any, **kwargs: Any) -> tuple[str, ...]:
        return ()


def strategy_rules(strategy: str) -> tuple[str, RetrievalRules]:
    """Resolve a harness strategy to its pipeline strategy and rules."""
    if strategy == "hybrid_rrf60":
        return "hybrid", replace(DEFAULT_RULES, fusion_offset=60)
    if strategy.startswith(WITHOUT_PREFIX):
        rule_id = strategy.removeprefix(WITHOUT_PREFIX)
        if rule_id not in RULE_IDS:
            raise ValueError(f"unknown retrieval rule: {rule_id}")
        return "hybrid", replace(DEFAULT_RULES, disabled=frozenset({rule_id}))
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown retrieval strategy: {strategy}")
    if strategy == "hybrid_no_graph":
        return "hybrid", DEFAULT_RULES
    return strategy, DEFAULT_RULES


@contextmanager
def real_retriever() -> Iterator[Retriever]:
    """One driver and event loop for the whole run; same composition as tests.support."""
    from neo4j import GraphDatabase

    adapters = importlib.import_module("app.adapters.retrieval")
    workflow = importlib.import_module("app.ai.retrieval")
    maintenance = importlib.import_module("app.bootstrap.maintenance")
    config = importlib.import_module("app.bootstrap.config").settings()
    loop = asyncio.new_event_loop()
    try:
        with GraphDatabase.driver(
            config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password)
        ) as graph:
            index = adapters.KnowledgeIndex(maintenance.connect, graph)

            def retrieve(strategy: str, question: str, locale: str) -> Record:
                pipeline_strategy, rules = strategy_rules(strategy)
                search_index = _NoGraph(index) if strategy == "hybrid_no_graph" else index
                search = workflow.PublicRetrieval(search_index, pipeline_strategy, rules=rules)
                evidence = loop.run_until_complete(search.search(question, locale))
                terms = tokens(question)
                sources = [
                    {
                        "key": canonical_key(item.path),
                        "path": item.path,
                        "start_line": item.start_line,
                        "score": float(
                            lexical_score(
                                {
                                    "path": item.path,
                                    "content": item.content,
                                    "start_line": item.start_line,
                                    "end_line": item.end_line,
                                    "url": item.url,
                                    "content_hash": "",
                                },
                                terms,
                                locale,
                            )
                        ),
                    }
                    for item in evidence
                ]
                return {
                    "sources": sources,
                    "commit_sha": evidence[0].commit_sha if evidence else None,
                }

            yield retrieve
    finally:
        loop.close()


def collect(
    retrieve: Retriever, queries: Sequence[Query], strategies: Sequence[str]
) -> dict[str, Records]:
    return {
        strategy: {q["id"]: retrieve(strategy, q["question"], q["locale"]) for q in queries}
        for strategy in strategies
    }


def run_harness(
    queries: Sequence[Query],
    qrels: Qrels,
    qrels_source: str,
    retrieve: Retriever,
    strategies: Sequence[str] = STRATEGIES,
    *,
    ablate: bool = False,
) -> dict[str, Any]:
    """Score selected strategies, optionally adding all paired ablations against hybrid."""
    if ablate:
        strategies = tuple(dict.fromkeys((*strategies, "hybrid", *ABLATION_STRATEGIES)))
    records = collect(retrieve, queries, strategies)
    per_query = {name: score_run(runs_from_records(recs), qrels) for name, recs in records.items()}
    commit = next(
        (
            r["commit_sha"]
            for recs in records.values()
            for r in recs.values()
            if r.get("commit_sha")
        ),
        None,
    )
    report = assemble_report(queries, qrels, qrels_source, records, per_query, commit=commit)
    if ablate:
        report["rule_ablation"] = _ablation_report(report, qrels)
    return report


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(finite(data), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def summary(report: dict[str, Any]) -> str:
    lines = [f"qrels: {report['qrels_source']}; queries: {report['queries']['scored']} scored"]
    for name, data in report["strategies"].items():
        overall = data["overall"]
        lines.append(
            f"{name:16} recall@5={overall['recall@5']:.3f} ndcg@5={overall['ndcg@5']:.3f} "
            f"mrr@10={overall['mrr@10']:.3f} hit@1={overall['hit@1']:.3f} "
            f"EN-ES gap={data['en_es_gap']['gap']:+.3f}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieval harness (ranx).")
    parser.add_argument("--queries", type=Path, default=QUERIES)
    parser.add_argument("--qrels", type=Path, default=QRELS)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--out", type=Path, default=Path("artifacts/retrieval-report.json"))
    parser.add_argument(
        "--strategies", nargs="+", choices=(*STRATEGIES, *ABLATION_STRATEGIES), default=STRATEGIES
    )
    baseline_mode = parser.add_mutually_exclusive_group()
    baseline_mode.add_argument(
        "--ablate",
        action="store_true",
        help="report paired deltas for every rule and RRF offset 60",
    )
    baseline_mode.add_argument(
        "--write-baseline",
        nargs="?",
        const=BASELINE,
        type=Path,
        help="store the report as the baseline (default evals/baselines/retrieval.json)",
    )
    parser.add_argument("--allow-proposed-qrels", action="store_true")
    parser.add_argument(
        "--compare",
        nargs="?",
        const=BASELINE,
        type=Path,
        help="paired ranx comparison with a baseline; exit 1 on a significant Recall@5 drop",
    )
    parser.add_argument(
        "--ablation",
        nargs="*",
        choices=sorted(ABLATIONS),
        help="ablations to list in the console; all are always recorded in the report",
    )
    args = parser.parse_args(argv)

    queries = load_queries(args.queries)
    qrels, source = load_qrels(args.qrels, args.candidates)
    if args.write_baseline and source != "resolved" and not args.allow_proposed_qrels:
        print(
            "refusing --write-baseline: qrels.jsonl is not resolved yet "
            "(use --allow-proposed-qrels only for a provisional baseline)",
            file=sys.stderr,
        )
        return 2
    with real_retriever() as retrieve:
        report = run_harness(queries, qrels, source, retrieve, args.strategies, ablate=args.ablate)
    print(summary(report))
    for name in args.ablation or ():
        print(f"ablation {name}: {ABLATIONS[name]['status']} ({ABLATIONS[name]['seam']})")

    exit_code = 0
    if args.compare:
        baseline = json.loads(args.compare.read_text(encoding="utf-8"))
        comparison = compare_reports(baseline, report["runs"], qrels, queries)
        report["comparison"] = comparison
        print(json.dumps(comparison, indent=2, sort_keys=True))
        exit_code = 1 if comparison["failed"] else 0
    write_json(args.out, report)
    if args.write_baseline:
        write_json(args.write_baseline, report)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
