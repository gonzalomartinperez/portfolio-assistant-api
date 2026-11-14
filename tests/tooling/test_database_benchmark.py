"""Opt-in benchmark guards do not acquire clients before prerequisite validation."""

import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import benchmark_database_queries as benchmark


def test_benchmark_requires_explicit_fixture_mutation_flag(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'scripts.benchmark_database_queries',
            '--output',
            str(tmp_path / 'report.json'),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert '--seed-owned-fixtures is required' in result.stderr
    assert not (tmp_path / 'report.json').exists()


@pytest.mark.parametrize(
    'changes',
    [
        {'ai_provider': 'openai'},
        {'embeddings_provider': 'openai'},
        {'allow_paid_ai': True},
    ],
)
def test_paid_configuration_never_reaches_owned_target_or_database(
    monkeypatch, tmp_path, changes
):
    def forbidden(*args):
        pytest.fail('invalid benchmark configuration reached target/client validation')

    monkeypatch.setattr(benchmark, 'validate_targets', forbidden)
    values = {
        'ai_provider': 'fixture',
        'embeddings_provider': 'fixture',
        'allow_paid_ai': False,
    } | changes
    with pytest.raises(ValueError, match='fixture-only'):
        benchmark.benchmark(SimpleNamespace(**values), tmp_path / 'report.json')
    assert not (tmp_path / 'report.json').exists()
