"""CI graph and real shell aggregate fail closed across negative outcomes."""

import os
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts.ci_profile import NEEDS, profile_errors


def workflow():
    return yaml.safe_load(Path('.github/workflows/quality.yml').read_text())


def test_actual_paired_profile_has_no_filtered_or_missing_required_work():
    assert profile_errors(workflow()) == []


@pytest.mark.parametrize('key', NEEDS)
def test_every_job_identity_and_dependency_is_required(key):
    value = workflow()
    del value['jobs'][key]
    assert profile_errors(value)
    value = workflow()
    value['jobs'][key]['name'] = 'successful placeholder'
    assert profile_errors(value)
    value = workflow()
    value['jobs'][key]['needs'] = ['unknown']
    assert profile_errors(value)


@pytest.mark.parametrize(
    'mode', ['paths', 'permissions', 'action', 'if', 'continue', 'gate']
)
def test_policy_cannot_hide_or_privilege_pr_work(mode):
    value = workflow()
    if mode == 'paths':
        value.get('on', value.get(True))['pull_request']['paths'] = ['app/**']
    elif mode == 'permissions':
        value['jobs']['container']['permissions'] = {'packages': 'write'}
    elif mode == 'action':
        value['jobs']['static']['steps'][0]['uses'] = 'actions/checkout@main'
    elif mode == 'if':
        value['jobs']['database']['if'] = 'false'
    elif mode == 'continue':
        value['jobs']['container']['steps'][0]['continue-on-error'] = True
    else:
        value['jobs']['checks']['steps'][0]['env'].pop('DATABASE_RESULT')
    assert profile_errors(value)


def test_actual_aggregate_shell_requires_each_expected_result():
    gate = workflow()['jobs']['checks']['steps'][0]
    green = {name: 'success' for name in gate['env']}
    assert (
        subprocess.run(
            ['bash', '-e', '-c', gate['run']],
            env={**os.environ, **green},
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    for key in green:
        for outcome in ('failure', 'cancelled', 'skipped', 'pending', ''):
            failed = {**green, key: outcome}
            assert (
                subprocess.run(
                    ['bash', '-e', '-c', gate['run']],
                    env={**os.environ, **failed},
                    capture_output=True,
                    check=False,
                ).returncode
                != 0
            )
        missing = deepcopy(green)
        del missing[key]
        clean_env = {
            name: value for name, value in os.environ.items() if name not in green
        }
        assert (
            subprocess.run(
                ['bash', '-e', '-c', gate['run']],
                env={**clean_env, **missing},
                capture_output=True,
                check=False,
            ).returncode
            != 0
        )


def test_identity_rejects_other_candidate_and_records_no_environment_values(
    tmp_path, monkeypatch
):
    from scripts import ci_identity

    for name in ci_identity.BUILD_INPUTS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('reviewed input')
    monkeypatch.setattr(
        ci_identity.subprocess, 'check_output', lambda *args, **kwargs: 'a' * 40
    )
    env = {
        'GITHUB_SHA': 'a' * 40,
        'GITHUB_WORKFLOW_SHA': 'b' * 40,
        'CI_BASE_SHA': 'c' * 40,
        'GITHUB_RUN_ID': '17',
        'GITHUB_RUN_ATTEMPT': '1',
        'PRIVATE_SENTINEL': 'never copied',
    }
    report = ci_identity.identity(tmp_path, env)
    assert report['source_sha'] == 'a' * 40
    assert report['base_sha'] == 'c' * 40
    assert set(report['build_inputs_sha256']) == set(ci_identity.BUILD_INPUTS)
    assert 'never copied' not in str(report)
    with pytest.raises(ValueError, match='candidate'):
        ci_identity.identity(tmp_path, {**env, 'GITHUB_SHA': 'd' * 40})


@pytest.mark.parametrize('result', [1, 128])
def test_dirty_or_unverifiable_build_inputs_fail_closed(result, tmp_path, monkeypatch):
    from scripts import ci_identity

    monkeypatch.setattr(
        ci_identity.subprocess,
        'run',
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], result),
    )
    assert not ci_identity.clean_build_inputs(tmp_path)


def test_target_branch_edits_require_fresh_candidate_verification():
    value = workflow()
    value.get('on', value.get(True))['pull_request']['types'].remove('edited')
    assert profile_errors(value)
