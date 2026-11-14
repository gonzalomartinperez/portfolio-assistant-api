import json

import pytest

from tests.load.run_load import BUDGET_KEYS, load_budgets, metrics, verdict

ROWS = {
    'stream': {'Request Count': '2000', 'Failure Count': '0'},
    'ttfe': {'95%': '120'},
    'gap': {'95%': '40'},
}
BUDGETS = {
    'ttfe_p95_ms': 1500,
    'gap_p95_ms': 500,
    'error_rate': 0.005,
    'rss_growth': 0.2,
}


def test_within_budget_passes():
    assert verdict(metrics(ROWS, 100, 110), BUDGETS, {}, 900, 30) == {}


def test_over_budget_fails_unless_baselined():
    rows = {**ROWS, 'ttfe': {'95%': '2000'}}
    measured = metrics(rows, 100, 150)
    assert set(verdict(measured, BUDGETS, {}, 900)) == {'ttfe_p95_ms', 'rss_growth'}
    assert set(verdict(measured, BUDGETS, {'ttfe_p95_ms': 2500}, 900)) == {'rss_growth'}


def test_rss_growth_only_applies_to_a_soak():
    assert verdict(metrics(ROWS, 100, 300), BUDGETS, {}, 20) == {}


def test_missing_rows_and_too_few_streams_fail():
    empty = verdict(metrics({}, 100, 100), BUDGETS, {}, 900, 30)
    assert {'ttfe_p95_ms', 'gap_p95_ms', 'streams'} <= set(empty)
    few = {**ROWS, 'stream': {'Request Count': '3', 'Failure Count': '0'}}
    assert set(verdict(metrics(few, 100, 100), BUDGETS, {}, 900, 30)) == {'streams'}


def test_setup_failures_count_as_errors():
    rows = {**ROWS, 'setup': {'Failure Count': '50'}}
    assert metrics(rows, 100, 100)['error_rate'] > 0.005


def test_budget_file_is_valid_and_rejects_bad_keys(tmp_path):
    assert set(load_budgets()['budgets']) == set(BUDGET_KEYS)
    for config in (
        {'budgets': {'ttfe_p95_ms': 1}, 'baseline': {}},
        {'budgets': dict.fromkeys(BUDGET_KEYS, 1), 'baseline': {'typo': 2}},
    ):
        path = tmp_path / 'b.json'
        path.write_text(json.dumps(config))
        with pytest.raises(ValueError):
            load_budgets(path)
