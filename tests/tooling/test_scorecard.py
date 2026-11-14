"""Scorecard collectors, ratchet check and tighten-only rewrite on synthetic artifacts."""

import json
from pathlib import Path

import pytest

from scorecard.__main__ import main
from scorecard.collect import collect

JUNIT = '<testsuites><testsuite tests="{t}" failures="{f}" errors="0" skipped="{s}"/></testsuites>'


def write_artifacts(directory: Path, failures: int = 0) -> None:
    directory.mkdir(exist_ok=True)
    (directory / 'ruff.json').write_text('[{"code": "E1"}, {"code": "E2"}]')
    (directory / 'mypy.txt').write_text(
        'Found 3 errors in 2 files (checked 5 source files)\n'
    )
    (directory / 'unit.xml').write_text(JUNIT.format(t=10, f=failures, s=1))
    (directory / 'integration.xml').write_text(JUNIT.format(t=5, f=0, s=0))
    (directory / 'coverage.xml').write_text(
        '<coverage line-rate="0.9" branch-rate="0.8"/>'
    )
    (directory / 'golden.json').write_text('{"passed": 9, "total": 10}')


def test_collectors_read_synthetic_artifacts(tmp_path):
    write_artifacts(tmp_path)
    m = collect(tmp_path, tmp_path)['metrics']
    assert m['static.ruff_findings']['value'] == 2
    assert m['static.mypy_errors']['value'] == 3
    assert m['tests.unit.total']['value'] == 10
    assert m['tests.unit.skipped']['value'] == 1
    assert m['tests.integration_share']['value'] == pytest.approx(5 / 15)
    assert m['coverage.branch_rate']['value'] == 0.8
    assert m['eval.golden_pass_rate']['value'] == 0.9


def test_mypy_success_line_means_zero(tmp_path):
    (tmp_path / 'mypy.txt').write_text('Success: no issues found in 39 source files\n')
    assert collect(tmp_path, tmp_path)['metrics']['static.mypy_errors']['value'] == 0


def test_missing_inputs_are_unmet_never_pass(tmp_path):
    result = collect(tmp_path / 'absent', tmp_path)
    assert all(v['status'] == 'missing' for v in result['metrics'].values())
    assert all(v['value'] is None for v in result['metrics'].values())
    assert {c['status'] for c in result['criteria'].values()} == {'unmet'}
    assert result['judged'] == {
        'source': None,
        'scores': None,
        'status': 'not yet scored',
    }


def test_criteria_pass_and_fail(tmp_path):
    write_artifacts(tmp_path)
    criteria = collect(tmp_path, tmp_path)['criteria']
    assert criteria['D2.mypy_errors']['status'] == 'fail'
    assert criteria['D3.branch_coverage']['status'] == 'fail'
    assert criteria['D3.tests_failing']['status'] == 'pass'
    assert criteria['D1.guard_violations']['status'] == 'unmet'


def test_judged_scores_come_from_the_latest_evidence_file(tmp_path):
    scores = tmp_path / 'docs/evidence/scores'
    scores.mkdir(parents=True)
    (scores / '2026-01-01.md').write_text('| D1 Architecture | 10 |\n')
    (scores / '2026-02-01.md').write_text(
        '| D1 Architecture | **82** |\n| P3 Quality | 50 |\n'
    )
    result = collect(tmp_path / 'none', tmp_path)
    assert result['judged']['scores'] == {'D1': 82, 'P3': 50}
    assert result['metrics']['judged.D1']['value'] == 82


def seed_ratchets(directory: Path, lower: float = 2, higher: float = 10) -> None:
    directory.mkdir()
    (directory / 'a.json').write_text(
        json.dumps(
            {
                'metrics': {
                    'static.ruff_findings': {'direction': 'lower', 'value': lower},
                    'tests.unit.total': {'direction': 'higher', 'value': higher},
                    'coverage.line_rate': {'direction': 'higher', 'value': None},
                }
            }
        )
    )


def run(tmp_path, command, *extra):
    artifacts = tmp_path / 'artifacts'
    write_artifacts(artifacts)
    current = tmp_path / 'scorecard.json'
    main(
        [
            'collect',
            '--artifacts',
            str(artifacts),
            '--out',
            str(current),
            '--root',
            str(tmp_path),
        ]
    )
    return main(
        [
            command,
            '--current',
            str(current),
            '--ratchets',
            str(tmp_path / 'r'),
            '--root',
            str(tmp_path),
            *extra,
        ]
    )


def test_check_passes_on_equal_and_improved(tmp_path, capsys):
    seed_ratchets(tmp_path / 'r', lower=2, higher=10)
    assert run(tmp_path, 'check') == 0
    out = capsys.readouterr().out
    assert 'unseeded' in out and 'ok' in out


def test_check_fails_on_regression_in_either_direction(tmp_path):
    seed_ratchets(tmp_path / 'r', lower=1, higher=10)
    assert run(tmp_path, 'check') == 1
    seed_ratchets(tmp_path / 'r2', lower=2, higher=11)
    (tmp_path / 'r').rename(tmp_path / 'r_old')
    (tmp_path / 'r2').rename(tmp_path / 'r')
    assert run(tmp_path, 'check') == 1


def test_check_unmet_fails_only_when_strict(tmp_path):
    seed_ratchets(tmp_path / 'r')
    (tmp_path / 'artifacts').mkdir()
    current = tmp_path / 'c.json'
    main(
        [
            'collect',
            '--artifacts',
            str(tmp_path / 'artifacts'),
            '--out',
            str(current),
            '--root',
            str(tmp_path),
        ]
    )
    args = [
        'check',
        '--current',
        str(current),
        '--ratchets',
        str(tmp_path / 'r'),
        '--root',
        str(tmp_path),
    ]
    assert main(args) == 0
    assert main([*args, '--strict']) == 1


def test_tighten_improves_but_never_loosens(tmp_path):
    seed_ratchets(tmp_path / 'r', lower=5, higher=20)
    assert run(tmp_path, 'tighten') == 0
    metrics = json.loads((tmp_path / 'r/a.json').read_text())['metrics']
    assert metrics['static.ruff_findings']['value'] == 2  # lower is better: 5 -> 2
    assert metrics['tests.unit.total']['value'] == 20  # measured 10 is worse: kept
    assert metrics['coverage.line_rate']['value'] == 0.9  # first seed from null


def test_pointer_ratchet_reads_the_image_budget(tmp_path):
    (tmp_path / 'img.json').write_text('{"api_max_bytes": 100}')
    (tmp_path / 'r').mkdir()
    (tmp_path / 'r/i.json').write_text(
        json.dumps(
            {
                'metrics': {
                    'image.api_bytes': {
                        'direction': 'lower',
                        'pointer': {'file': 'img.json', 'key': 'api_max_bytes'},
                    }
                }
            }
        )
    )
    current = tmp_path / 'c.json'
    current.write_text(json.dumps({'metrics': {'image.api_bytes': {'value': 101}}}))
    args = [
        '--current',
        str(current),
        '--ratchets',
        str(tmp_path / 'r'),
        '--root',
        str(tmp_path),
    ]
    assert main(['check', *args]) == 1


def test_committed_ratchets_are_valid_and_declare_directions():
    files = sorted(Path('scorecard/ratchets').glob('*.json'))
    assert {f.stem for f in files} >= {
        'static',
        'tests',
        'coverage',
        'image',
        'scorecard',
    }
    for file in files:
        for name, entry in json.loads(file.read_text())['metrics'].items():
            assert entry['direction'] in ('lower', 'higher'), name
            assert entry.get('source'), name
            assert 'pointer' in entry or 'value' in entry, name
