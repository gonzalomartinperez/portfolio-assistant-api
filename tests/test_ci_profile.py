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
    'mode', ['paths', 'permissions', 'action', 'if', 'continue', 'gate', 'runner']
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
    elif mode == 'runner':
        value['jobs']['database']['runs-on'] = 'ubuntu-latest'
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


@pytest.mark.parametrize(
    'mutation',
    [
        'missing',
        'filtered',
        'wrong_report',
        'fixable_only',
        'hidden_summary',
        'shell',
        'step_shell',
        'job_shell',
    ],
)
def test_postgres_inventory_cannot_hide_unfixed_critical_findings(mutation):
    value = workflow()
    step = next(
        step
        for step in value['jobs']['container']['steps']
        if step.get('name')
        == 'Inventory PostgreSQL and reject critical or fixable high findings'
    )
    if mutation == 'missing':
        step['run'] = 'true'
    elif mutation == 'filtered':
        step['run'] += '\n# --ignore-unfixed\n'
    elif mutation == 'wrong_report':
        step['run'] = step['run'].replace(
            '--report artifacts/postgres-vulnerabilities.json',
            '--report artifacts/image-vulnerabilities.json',
        )
    elif mutation == 'fixable_only':
        step['run'] = step['run'].replace(
            'python -m scripts.image_security',
            'python -m scripts.fixable_critical_only',
        )
    elif mutation == 'hidden_summary':
        step['run'] = step['run'].replace(
            '| tee artifacts/postgres-security-summary.json',
            '> artifacts/postgres-security-summary.json',
        )
    elif mutation == 'step_shell':
        step['shell'] = 'sh'
    elif mutation == 'job_shell':
        value['jobs']['container']['defaults'] = {'run': {'shell': 'sh'}}
    else:
        value['defaults']['run']['shell'] = 'sh'
    assert profile_errors(value)


POSTGRES_CACHE_EXPORT = (
    "${{ github.event_name == 'push' && "
    "(github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main') "
    "&& 'type=gha,version=2,mode=max,scope=postgres-linux-amd64' || '' }}"
)


def assert_postgres_cache_policy(value):
    exporters = [
        (key, step.get('name'), step['with']['cache-to'])
        for key, job in value['jobs'].items()
        for step in job.get('steps', [])
        if step.get('uses', '').startswith('docker/build-push-action@')
        and 'scope=postgres-linux-amd64'
        in str(step.get('with', {}).get('cache-to', ''))
    ]
    assert exporters == [
        (
            'container',
            'Build and load the isolated PostgreSQL fixture',
            POSTGRES_CACHE_EXPORT,
        )
    ]
    for key in ('database', 'container'):
        steps = value['jobs'][key]['steps']
        builders = [
            step
            for step in steps
            if step.get('uses', '').startswith('docker/setup-buildx-action@')
        ]
        assert len(builders) == 1
        assert builders[0]['with'] == {
            'version': 'v0.38.0',
            'driver-opts': 'image=moby/buildkit@sha256:cec9f139f45e93c5c69c60f8b07cfad9f43f4ef6b6a6cd917527fea5ff2e3dea',
        }
        builds = [
            step
            for step in steps
            if step.get('name') == 'Build and load the isolated PostgreSQL fixture'
        ]
        assert len(builds) == 1
        build = builds[0]
        assert (
            build['uses']
            == 'docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc'
        )
        expected = {
            'context': '.',
            'file': 'infra/docker/postgres/Dockerfile',
            'platforms': 'linux/amd64',
            'load': True,
            'push': False,
            'tags': 'portfolio-assistant-postgres:18.6',
            'cache-from': 'type=gha,version=2,scope=postgres-linux-amd64',
        }
        if key == 'container':
            expected['cache-to'] = POSTGRES_CACHE_EXPORT
        assert build['with'] == expected
        assert 'if' not in build
        starts = [step for step in steps if step.get('id') == 'postgres']
        assert len(starts) == 1
        start = starts[0]
        assert steps.index(builders[0]) < steps.index(build) < steps.index(start)
        assert start['run'].splitlines()[0] == (
            'docker compose -f infra/compose/local.yaml -p assistant-ci '
            'up --no-build --pull never -d --wait --wait-timeout 90 postgres'
        )


def test_postgres_cache_never_replaces_build_or_service_verification():
    assert_postgres_cache_policy(workflow())


@pytest.mark.parametrize('key', ['database', 'container'])
@pytest.mark.parametrize(
    'mutation',
    [
        'platform',
        'scope',
        'load',
        'push',
        'writer',
        'skip',
        'order',
        'rebuild',
        'pull',
        'buildx',
        'buildkit',
    ],
)
def test_postgres_cache_rejects_unbound_or_untrusted_execution(key, mutation):
    value = workflow()
    steps = value['jobs'][key]['steps']
    build = next(
        step
        for step in steps
        if step.get('name') == 'Build and load the isolated PostgreSQL fixture'
    )
    builder = next(
        step
        for step in steps
        if step.get('uses', '').startswith('docker/setup-buildx-action@')
    )
    start = next(step for step in steps if step.get('id') == 'postgres')
    if mutation == 'platform':
        build['with']['platforms'] = 'linux/arm64'
    elif mutation == 'scope':
        build['with']['cache-from'] = 'type=gha,scope=api-linux-amd64'
    elif mutation in ('load', 'push'):
        build['with'][mutation] = mutation == 'push'
    elif mutation == 'writer':
        build['with']['cache-to'] = (
            'type=gha,version=2,mode=max,scope=postgres-linux-amd64'
        )
    elif mutation == 'skip':
        build['if'] = 'false'
    elif mutation == 'order':
        steps.remove(build)
        steps.append(build)
    elif mutation == 'rebuild':
        start['run'] = start['run'].replace('--no-build', '--build')
    elif mutation == 'pull':
        start['run'] = start['run'].replace('--pull never', '--pull always')
    elif mutation == 'buildx':
        builder['with']['version'] = 'latest'
    else:
        builder['with']['driver-opts'] = 'image=moby/buildkit:latest'
    with pytest.raises(AssertionError):
        assert_postgres_cache_policy(value)


@pytest.mark.parametrize('mutation', ['extra_exporter', 'application_scope'])
def test_postgres_cache_rejects_exporters_under_other_step_names(mutation):
    value = workflow()
    if mutation == 'extra_exporter':
        steps = value['jobs']['database']['steps']
        extra = deepcopy(
            next(
                step
                for step in steps
                if step.get('name') == 'Build and load the isolated PostgreSQL fixture'
            )
        )
        extra['name'] = 'Unexpected second exporter'
        extra['with']['cache-to'] = POSTGRES_CACHE_EXPORT
        steps.append(extra)
    else:
        app = next(
            step
            for step in value['jobs']['container']['steps']
            if step.get('with', {}).get('file') == 'infra/docker/app/Dockerfile'
        )
        app['with']['cache-to'] = POSTGRES_CACHE_EXPORT
    with pytest.raises(AssertionError):
        assert_postgres_cache_policy(value)
