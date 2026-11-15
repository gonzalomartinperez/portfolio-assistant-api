import json
from pathlib import Path

import pytest

from evals.harness.qrels_resolve import (
    QrelsError,
    cohen_kappa,
    main,
    read_labels,
    resolve,
)


def write(path: Path, rows: list[tuple[str, str, int]]) -> Path:
    path.write_text(
        "".join(json.dumps({"query_id": q, "key": k, "relevance": r}) + "\n" for q, k, r in rows),
        encoding="utf-8",
    )
    return path


A = [("q1", "en/projects", 2), ("q1", "en/experience", 1), ("q2", "es/profile", 0)]


def test_kappa_perfect_chance_and_degenerate():
    assert cohen_kappa([0, 1, 2], [0, 1, 2]) == 1.0
    assert cohen_kappa([1, 1], [1, 1]) == 1.0
    assert cohen_kappa([0, 0, 1, 1], [0, 1, 0, 1]) == 0.0
    # two labellers who each use one label but different ones never agree
    assert cohen_kappa([0, 0], [1, 1]) == 0.0


def test_kappa_known_value():
    first = [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    second = [1, 1, 0, 0, 0, 0, 0, 0, 0, 1]
    # observed 0.8, expected 0.3*0.3 + 0.7*0.7 = 0.58 -> (0.8-0.58)/0.42
    assert cohen_kappa(first, second) == pytest.approx(0.5238, abs=1e-4)


def test_kappa_rejects_empty_or_mismatched():
    with pytest.raises(ValueError):
        cohen_kappa([], [])
    with pytest.raises(ValueError):
        cohen_kappa([0], [0, 1])


def test_resolve_agreement_and_resolution(tmp_path):
    a = read_labels(write(tmp_path / "a.jsonl", A))
    b = read_labels(
        write(
            tmp_path / "b.jsonl",
            [
                ("q1", "en/projects", 2),
                ("q1", "en/experience", 0),
                ("q2", "es/profile", 0),
            ],
        )
    )
    resolved, stats = resolve(a, b, {("q1", "en/experience"): 1})
    assert resolved[("q1", "en/experience")] == 1
    assert resolved[("q1", "en/projects")] == 2
    assert stats["pairs"] == 3
    assert stats["disagreements"] == 1
    assert stats["agreement_rate"] == pytest.approx(0.6667, abs=1e-4)
    assert stats["queries"] == 2
    assert stats["resolved"] == {0: 1, 1: 1, 2: 1}


def test_unresolved_disagreement_is_an_error(tmp_path):
    a = read_labels(write(tmp_path / "a.jsonl", A))
    b = read_labels(write(tmp_path / "b.jsonl", [(q, k, 0) for q, k, _ in A]))
    with pytest.raises(QrelsError, match="without a resolution"):
        resolve(a, b, {})


def test_pairs_must_match_and_resolution_must_be_needed(tmp_path):
    a = read_labels(write(tmp_path / "a.jsonl", A))
    b = read_labels(write(tmp_path / "b.jsonl", A[:2]))
    with pytest.raises(QrelsError, match="only labelled by A"):
        resolve(a, b, {})
    with pytest.raises(QrelsError, match="without a disagreement"):
        resolve(a, a, {("q1", "en/projects"): 1})


@pytest.mark.parametrize(
    "row",
    [
        {"query_id": "q", "key": "en/projects", "relevance": 3},
        {"query_id": "q", "key": "en/projects", "relevance": True},
        {"query_id": "q", "key": "fr/projects", "relevance": 1},
        {"query_id": "q", "relevance": 1},
    ],
)
def test_invalid_rows_are_rejected(tmp_path, row):
    path = tmp_path / "x.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(QrelsError):
        read_labels(path)


def test_duplicate_rows_are_rejected(tmp_path):
    with pytest.raises(QrelsError, match="duplicate"):
        read_labels(write(tmp_path / "d.jsonl", [A[0], A[0]]))


def test_cli_writes_qrels_and_stats(tmp_path):
    a = write(tmp_path / "a.jsonl", A)
    b = write(tmp_path / "b.jsonl", [("q1", "en/projects", 1), *A[1:]])
    c = write(tmp_path / "c.jsonl", [("q1", "en/projects", 2)])
    out, stats = tmp_path / "qrels.jsonl", tmp_path / "stats.json"
    code = main(
        ["--a", str(a), "--b", str(b), "--resolution", str(c), "--out", str(out)]
        + ["--stats", str(stats)]
    )
    assert code == 0
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert {(r["query_id"], r["key"]): r["relevance"] for r in rows}[("q1", "en/projects")] == 2
    assert json.loads(stats.read_text())["disagreements"] == 1
    # without the resolution file the same inputs fail and write nothing new
    out2 = tmp_path / "again.jsonl"
    assert main(["--a", str(a), "--b", str(b), "--out", str(out2), "--stats", str(stats)]) == 1
    assert not out2.exists()
