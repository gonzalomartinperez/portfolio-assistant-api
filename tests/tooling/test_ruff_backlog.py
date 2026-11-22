"""Ruff backlog counts map rule codes onto the target families of standards.md."""

from scripts.ruff_backlog import TARGET, family, summarize


def test_codes_map_to_the_longest_target_family():
    assert family("T201") == "T20"
    assert family("C420") == "C4"
    assert family("PTH105") == "PTH"
    assert family("PT011") == "PT"
    assert family("D213") == "D"
    assert family("XYZ1") == "XYZ"


def test_summary_lists_every_target_family_with_zero_defaults():
    summary = summarize([{"code": "T201"}, {"code": "T201"}, {"code": "S105"}])
    assert summary["total"] == 3
    by_family = summary["by_family"]
    assert isinstance(by_family, dict)
    assert set(by_family) == set(TARGET)
    assert by_family["T20"] == 2
    assert by_family["S"] == 1
    assert by_family["B"] == 0


def test_no_family_exceeds_its_committed_ratchet():
    """The nightly scorecard fails on a regressed family; catch it on the pull request instead."""
    import json

    from scripts.ruff_backlog import run_ruff
    from tests.support import ROOT

    metrics = json.loads((ROOT / "scorecard/ratchets/static.json").read_text())["metrics"]
    by_family = summarize(run_ruff())["by_family"]
    assert isinstance(by_family, dict)
    over = {
        name: (count, metrics[f"static.ruff_backlog.{name}"]["value"])
        for name, count in by_family.items()
        if f"static.ruff_backlog.{name}" in metrics
        and count > metrics[f"static.ruff_backlog.{name}"]["value"]
    }
    assert not over, f"family: (current, ratchet) {over}"
