"""Budget check: declared ceilings plus the 20% regression rule (assistant-quality.md section 11)."""

import json
from pathlib import Path

import pytest

from evals.harness.budgets import check_budgets, load_budgets, p95

LIMITS = {'first_delta_ms_p95': 250, 'tokens_in_p95': 6000, 'llm_calls_per_turn': 6}


def budgets(measured=None):
    return {'limits': LIMITS, 'measured': measured or {}}


def test_committed_baseline_declares_the_section_11_limits():
    loaded = load_budgets()
    assert loaded['limits'] == {
        'first_delta_ms_p95': 250,
        'answer_ms_p95': 1000,
        'retrieval_ms_p95': 400,
        'tokens_in_p95': 6000,
        'tokens_out_p95': 800,
        'cost_usd_p95': 0.02,
        'llm_calls_per_turn': 6,
    }
    assert loaded['measured'] == {}
    raw = json.loads(Path('evals/baselines/budgets.json').read_text())
    assert raw['source'].startswith('PROVISIONAL')


def test_within_limits_passes_and_the_limit_itself_is_allowed():
    assert check_budgets(LIMITS, budgets()) == []


def test_over_the_declared_limit_fails():
    problems = check_budgets({**LIMITS, 'tokens_in_p95': 6001}, budgets())
    assert len(problems) == 1 and 'tokens_in_p95' in problems[0]


def test_more_than_20_percent_over_the_measured_baseline_fails():
    base = budgets({'first_delta_ms_p95': 100})
    assert check_budgets({**LIMITS, 'first_delta_ms_p95': 120}, base) == []
    problems = check_budgets({**LIMITS, 'first_delta_ms_p95': 120.5}, base)
    assert len(problems) == 1 and 'regressed' in problems[0]


def test_unobserved_declared_metric_fails_closed():
    observed = {k: v for k, v in LIMITS.items() if k != 'llm_calls_per_turn'}
    assert check_budgets(observed, budgets()) == ['llm_calls_per_turn: not observed']


def test_p95_is_nearest_rank():
    assert p95([5]) == 5
    assert p95(list(range(1, 101))) == 95
    assert p95([3, 1, 2]) == 3
    with pytest.raises(ValueError):
        p95([])


def test_loader_rejects_bad_files(tmp_path):
    path = tmp_path / 'b.json'
    path.write_text('{"limits": {"a": 0}}')
    with pytest.raises(ValueError):
        load_budgets(path)
    path.write_text('{"limits": {"a": 1}, "measured": {"b": 1}}')
    with pytest.raises(ValueError):
        load_budgets(path)
