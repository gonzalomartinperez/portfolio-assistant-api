"""Mutation gates use deterministic evidence, never launch a campaign in tests."""

from collections import Counter
from datetime import date

import pytest

from scripts.mutation_gate import changed_scope, evaluate, parse_results


def baseline(ratchet=70):
    return {
        "break": 60,
        "warn_until": "2026-11-28",
        "groups": {"domain": {"ratchet": ratchet, "target": 75}},
    }


def test_results_group_by_package_and_do_not_credit_timeouts():
    output = """
 portfolio_assistant.domain.budget.x_cost__mutmut_1: killed
 portfolio_assistant.domain.budget.x_cost__mutmut_2: timeout
 portfolio_assistant.application.answer.x_run__mutmut_1: survived
 portfolio_assistant.ai.retrieval.x_search__mutmut_1: no tests
 evals.harness.graders.x_grade__mutmut_1: killed
 portfolio_assistant.domain.privacy.x_clean__mutmut_1: not checked
"""
    groups = parse_results(output)
    assert groups["domain"] == Counter(killed=1, timeout=1)
    assert set(groups) == {"domain", "application", "ai", "graders"}
    messages, failed = evaluate(
        groups={"domain": groups["domain"]},
        baseline=baseline(),
        today=date(2026, 11, 29),
    )
    assert failed
    assert "50.00%" in messages[0]


@pytest.mark.parametrize(
    "output",
    [
        "",
        "garbage",
        "portfolio_assistant.domain.x: new status",
        "tests.x: killed",
        "portfolio_assistant.domain.x: not checked",
        "portfolio_assistant.domain.x: killed\nportfolio_assistant.domain.x: killed",
    ],
)
def test_invalid_or_empty_evidence_fails(output):
    with pytest.raises(ValueError):
        parse_results(output)


@pytest.mark.parametrize(
    ("today", "enforce", "warn", "failed"),
    [
        (date(2026, 11, 14), False, False, False),
        (date(2026, 11, 28), False, True, False),
        (date(2026, 11, 29), False, True, True),
        (date(2026, 11, 14), True, True, True),
    ],
)
def test_warning_expires_and_enforcement_wins(today, enforce, warn, failed):
    messages, result = evaluate(
        {"domain": Counter(killed=6, survived=4)},
        baseline(),
        today,
        enforce=enforce,
        warn=warn,
    )
    assert result is failed
    assert "shortfall 10.00" in messages[0]


@pytest.mark.parametrize(
    ("killed", "ratchet", "failed"),
    [(6, None, False), (5, None, True), (7, 70, False), (6, 70, True)],
)
def test_break_floor_and_measured_ratchet(killed, ratchet, failed):
    _, result = evaluate(
        {"domain": Counter(killed=killed, survived=10 - killed)},
        baseline(ratchet),
        date(2026, 11, 29),
    )
    assert result is failed


def test_warning_period_cannot_be_extended():
    spec = baseline()
    spec["warn_until"] = "2026-11-29"
    with pytest.raises(ValueError):
        evaluate({"domain": Counter(killed=1)}, spec, date(2026, 11, 14))


def test_changed_selection_excludes_tests_unscoped_and_non_python():
    assert changed_scope(
        [
            "tests/unit/test_budget.py",
            "src/portfolio_assistant/domain/budget.py",
            "src/portfolio_assistant/adapters/client.py",
            "README.md",
        ],
        ["src/portfolio_assistant/domain/budget.py"],
    ) == ["src/portfolio_assistant/domain/budget.py"]


def test_changed_files_run_is_held_to_the_break_floor_not_the_ratchet():
    groups = {"domain": Counter(killed=65, survived=35)}
    _, full_failed = evaluate(groups, baseline(ratchet=75), date(2026, 11, 22), enforce=True)
    _, pr_failed = evaluate(
        groups, baseline(ratchet=75), date(2026, 11, 22), enforce=True, changed=True
    )
    assert full_failed
    assert not pr_failed


def test_changed_files_run_still_fails_below_the_break_floor():
    groups = {"domain": Counter(killed=59, survived=41)}
    _, failed = evaluate(groups, baseline(), date(2026, 11, 22), enforce=True, changed=True)
    assert failed


def test_mutation_sandbox_never_copies_the_sealed_holdout():
    import tomllib
    from pathlib import Path

    copied = tomllib.loads(Path("pyproject.toml").read_text())["tool"]["mutmut"]["also_copy"]
    assert "evals" not in copied
    assert not [entry for entry in copied if entry.startswith("evals/full")]
    expected = {
        f"evals/{child.name}"
        for child in Path("evals").iterdir()
        if child.name not in {"full", "__pycache__"}
    }
    assert expected <= set(copied)
