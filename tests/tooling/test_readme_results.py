"""README results table: rendering from a scorecard and sync with the committed snapshot."""

import json
from pathlib import Path

import pytest

from scripts.readme_results import (
    END,
    START,
    UNMEASURED,
    latest_snapshot,
    main,
    render_table,
    replace_block,
)

SNAPSHOT = "docs/evidence/scorecard-2000-01-01.json"


def metric(value):
    return {"value": value, "status": "ok" if value is not None else "missing"}


def scorecard(**values):
    keys = {
        "static.ruff_findings": 0,
        "static.mypy_errors": 0,
        "static.mypy_strict_app_errors": 89,
        "tests.unit.total": 1234,
        "tests.unit.failures": 0,
        "tests.unit.skipped": 7,
        "coverage.branch_rate": 0.875,
    }
    keys.update(values)
    return {"schema": 1, "metrics": {key: metric(value) for key, value in keys.items()}}


def test_table_renders_measured_values_and_marks_the_rest_unmeasured(tmp_path):
    table = render_table(scorecard(), tmp_path, SNAPSHOT)
    lines = table.splitlines()
    assert "| Check | Result | Source |" in lines
    assert f"| Lint (ruff) | 0 findings | [`static.ruff_findings`]({SNAPSHOT}) |" in lines
    assert any("| Types (mypy --strict src) | 89 errors |" in line for line in lines)
    assert any("1,234 tests, 0 failed, 7 skipped" in line for line in lines)
    assert any("Branch coverage (offline lane) | 87.5%" in line for line in lines)
    for check in ("Integration tests", "Golden replay pass rate", "Mutation score"):
        assert any(line.startswith(f"| {check} | {UNMEASURED} |") for line in lines), check
    assert any(line.startswith(f"| Image size | {UNMEASURED} |") for line in lines)


def test_a_failed_or_missing_status_is_never_rendered_as_a_number(tmp_path):
    card = scorecard()
    card["metrics"]["static.mypy_errors"] = {"value": 3, "status": "missing"}
    table = render_table(card, tmp_path, SNAPSHOT)
    assert f"| Types (mypy) | {UNMEASURED} |" in table


def test_baseline_rows_are_read_from_committed_files_only(tmp_path):
    assert "Golden set size" not in render_table(scorecard(), tmp_path, SNAPSHOT)
    (tmp_path / "evals/golden").mkdir(parents=True)
    (tmp_path / "evals/golden/manifest.json").write_text(
        json.dumps({"item_count": 5, "counts": {"locales": {"en": 3, "es": 2}}})
    )
    table = render_table(scorecard(), tmp_path, SNAPSHOT)
    assert "| Golden set size | 5 items (EN 3, ES 2) |" in table


def test_replace_block_keeps_the_surrounding_text_and_is_idempotent():
    readme = f"before\n{START}\nold\n{END}\nafter\n"
    once = replace_block(readme, "table")
    assert once == f"before\n{START}\ntable\n{END}\nafter\n"
    assert replace_block(once, "table") == once
    with pytest.raises(ValueError):
        replace_block("no markers", "table")


def test_write_then_check_round_trip(tmp_path):
    snapshot = tmp_path / "docs/evidence/scorecard-2000-01-01.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text(json.dumps(scorecard()))
    readme = tmp_path / "README.md"
    readme.write_text(f"{START}\nstale\n{END}\n")
    args = ["--root", str(tmp_path)]
    assert main([*args, "--check"]) == 1
    assert main([*args, "--write"]) == 0
    assert main([*args, "--check"]) == 0
    assert latest_snapshot(tmp_path) == snapshot
    assert main(["--root", str(tmp_path / "missing"), "--check"]) == 2


def test_committed_readme_is_in_sync_with_the_committed_snapshot():
    assert Path(SNAPSHOT.replace("2000-01-01", "2026-11-14")).exists()
    assert main(["--check"]) == 0
