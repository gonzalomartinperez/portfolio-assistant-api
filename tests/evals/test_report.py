"""Report aggregation and the private report file."""

import json
import stat

import pytest

from evals.harness.report import ItemOutcome, build_report, write_report
from evals.harness.result import GradeResult

SECRET = 'RAW-ANSWER-TEXT-SHOULD-NEVER-APPEAR'


def outcome(item_id, locale, strata, *passed):
    grades = tuple(GradeResult(f'g{i}', ok, SECRET) for i, ok in enumerate(passed))
    return ItemOutcome(item_id, locale, tuple(strata), grades)


OUTCOMES = [
    outcome('a-en-1', 'en', ['core'], True, True),
    outcome('a-es-1', 'es', ['core'], True, False),
    outcome('b-es-1', 'es', ['core', 'abstain'], False),
]


def test_report_counts_per_stratum_and_locale_and_failures():
    report = build_report(OUTCOMES, tier='golden', run_id='r1')
    assert report['totals'] == {'total': 3, 'passed': 1}
    assert report['by_locale'] == {
        'en': {'total': 1, 'passed': 1},
        'es': {'total': 2, 'passed': 0},
    }
    strata = report['by_stratum']
    assert strata['core']['by_locale']['es'] == {'total': 2, 'passed': 0}  # type: ignore[index]
    assert strata['abstain']['total'] == 1  # type: ignore[index]
    assert report['failing_ids_by_stratum'] == {
        'abstain': ['b-es-1'],
        'core': ['a-es-1', 'b-es-1'],
    }
    assert report['failed_assertions'] == {'a-es-1': ['g1'], 'b-es-1': ['g0']}
    assert report['pins'] == {}


def test_report_records_optional_pins_and_never_details():
    report = build_report(
        OUTCOMES, tier='golden', run_id='r1', pins={'corpus': 'corpus-abc'}
    )
    assert report['pins'] == {'corpus': 'corpus-abc'}
    assert SECRET not in json.dumps(report)


def test_all_passing_report_has_no_failures():
    report = build_report(OUTCOMES[:1], tier='full', run_id='r2')
    assert report['failing_ids_by_stratum'] == {}
    assert report['failed_assertions'] == {}


def test_write_report_is_private_and_refuses_to_overwrite(tmp_path):
    report = build_report(OUTCOMES, tier='golden', run_id='r1')
    path = write_report(report, tmp_path / 'artifacts' / 'eval')
    assert path.name == 'golden-r1.json'
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == json.loads(json.dumps(report))
    with pytest.raises(FileExistsError):
        write_report(report, tmp_path / 'artifacts' / 'eval')
