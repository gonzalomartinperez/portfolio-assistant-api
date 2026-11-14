"""Dynamic CI profiles, the fail-closed gate and the profile map stay consistent."""

import json
import os
import re
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts.ci_profile import GATED, NAMES, profile_errors, standalone_errors


def workflow():
    return yaml.safe_load(Path('.github/workflows/ci.yml').read_text())


def profile_map():
    return json.loads(Path('.github/ci-profile.json').read_text())


def glob_to_regex(pattern):
    """Same semantics as the shared classifier: `**/` any dirs, `**` anything, `*` one segment."""
    out, i = '', 0
    while i < len(pattern):
        if pattern.startswith('**/', i):
            out += '(?:.*/)?'
            i += 3
        elif pattern.startswith('**', i):
            out += '.*'
            i += 2
        elif pattern[i] == '*':
            out += '[^/]*'
            i += 1
        elif pattern[i] == '?':
            out += '[^/]'
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r'\Z')


def matching_profiles(path, profiles=None):
    profiles = profiles or profile_map()['profiles']
    return [
        name
        for name, spec in profiles.items()
        if any(glob_to_regex(pattern).match(path) for pattern in spec.get('paths', []))
    ]


def tracked_files():
    output = subprocess.run(
        ['git', 'ls-files', '-z'], capture_output=True, check=True, text=True
    ).stdout
    return [path for path in output.split('\0') if path and Path(path).exists()]


def test_actual_profile_has_no_filtered_or_missing_required_work():
    assert profile_errors(workflow(), profile_map()) == []


def test_profile_map_is_valid_json_with_the_expected_keys():
    value = profile_map()
    assert set(value) == {'base', 'required', 'profiles'}
    assert value['base'] == ['secrets', 'security']
    assert value['required'] == 'ci-gate'
    assert set(value['profiles']) == {
        'docs',
        'harness',
        'workflow',
        'code',
        'deps-weekly',
        'release',
        'hotfix',
    }
    for name in ('docs', 'harness', 'workflow', 'code'):
        spec = value['profiles'][name]
        assert spec['paths'] and spec['adds']
        assert spec['budgetP50Minutes'] < spec['budgetP95Minutes']
    assert value['profiles']['docs']['adds'] == ['static']
    assert value['profiles']['deps-weekly']['adds'] == ['all-profiles']
    assert value['profiles']['release']['adds'] == ['all-profiles']
    assert 'dependabot/**' in value['profiles']['deps-weekly']['trigger']
    assert 'main' in value['profiles']['release']['trigger']


def test_every_tracked_file_matches_at_least_one_profile():
    unmatched = [path for path in tracked_files() if not matching_profiles(path)]
    assert unmatched == []


def test_unknown_paths_match_no_profile_so_classify_fails_closed():
    assert matching_profiles('unknown/new-file.bin') == []
    assert matching_profiles('new-top-level.bin') == []


@pytest.mark.parametrize(
    'path',
    [
        'app/main.py',
        'tests/test_x.py',
        'scripts/tool.py',
        'migrations/001.sql',
        'contracts/schema.json',
    ],
)
def test_docs_profile_never_matches_code_unless_markdown(path):
    assert 'docs' not in matching_profiles(path)
    assert 'code' in matching_profiles(path)
    assert 'docs' in matching_profiles(path.rsplit('.', 1)[0] + '.md')


@pytest.mark.parametrize(
    'directory', ['app', 'tests', 'scripts', 'migrations', 'contracts']
)
def test_docs_profile_only_matches_markdown_under_code_directories(directory):
    docs = profile_map()['profiles']['docs']['paths']
    for path in tracked_files():
        if path.startswith(directory + '/') and not path.endswith('.md'):
            assert not any(glob_to_regex(pattern).match(path) for pattern in docs), path


def test_profiles_run_the_documented_jobs():
    profiles = profile_map()['profiles']
    assert profiles['docs']['adds'] == ['static']
    assert profiles['harness']['adds'] == ['static']
    assert set(profiles['code']['adds']) == {'static', 'database', 'container'}
    assert set(profiles['workflow']['adds']) == set(GATED) - {'security'}


@pytest.mark.parametrize('key', NAMES)
def test_every_job_identity_is_required(key):
    value = workflow()
    del value['jobs'][key]
    assert profile_errors(value, profile_map())
    value = workflow()
    value['jobs'][key]['name'] = 'successful placeholder'
    assert profile_errors(value, profile_map())


@pytest.mark.parametrize('key', GATED)
def test_gated_jobs_require_classify_and_their_own_id(key):
    value = workflow()
    value['jobs'][key]['needs'] = [
        name for name in value['jobs'][key]['needs'] if name != 'classify'
    ]
    assert profile_errors(value, profile_map())
    value = workflow()
    del value['jobs'][key]['if']
    assert profile_errors(value, profile_map())
    value = workflow()
    other = next(name for name in GATED if name != key)
    value['jobs'][key]['if'] = (
        f"contains(fromJSON(needs.classify.outputs.jobs), '{other}')"
    )
    assert profile_errors(value, profile_map())


def test_secrets_cannot_be_gated():
    value = workflow()
    value['jobs']['secrets']['if'] = (
        "contains(fromJSON(needs.classify.outputs.jobs), 'secrets')"
    )
    assert profile_errors(value, profile_map())


def test_ci_gate_must_always_run():
    value = workflow()
    del value['jobs']['ci-gate']['if']
    assert profile_errors(value, profile_map())


@pytest.mark.parametrize(
    'dropped', [k for k in NAMES if k not in ('ci-gate', 'checks')]
)
def test_ci_gate_must_need_every_other_job(dropped):
    value = workflow()
    value['jobs']['ci-gate']['needs'].remove(dropped)
    assert profile_errors(value, profile_map())


def test_checks_alias_needs_only_ci_gate():
    value = workflow()
    value['jobs']['checks']['needs'] = ['ci-gate', 'static']
    assert profile_errors(value, profile_map())


def test_shared_building_blocks_must_pin_the_same_sha():
    value = workflow()
    step = value['jobs']['ci-gate']['steps'][0]
    pinned = step['uses'].split('@', 1)[1].split()[0]
    step['uses'] = step['uses'].replace(pinned, 'f' * 40)
    assert profile_errors(value, profile_map())
    value = workflow()
    value['jobs']['classify']['uses'] = (
        'gonzalomartinperez/engineering-standards/.github/workflows/classify.yml@main'
    )
    assert profile_errors(value, profile_map())


def test_profile_map_cannot_name_missing_jobs_or_weaken_the_gate():
    value = profile_map()
    value['profiles']['code']['adds'].append('missing-job')
    assert profile_errors(workflow(), value)
    value = profile_map()
    value['required'] = 'checks'
    assert profile_errors(workflow(), value)
    value = profile_map()
    value['profiles']['release']['adds'] = ['static']
    assert profile_errors(workflow(), value)


@pytest.mark.parametrize(
    'mode',
    ['paths', 'permissions', 'action', 'continue', 'runner', 'target', 'timeout'],
)
def test_policy_cannot_hide_or_privilege_pr_work(mode):
    value = workflow()
    events = value.get('on', value.get(True))
    if mode == 'paths':
        events['pull_request']['paths'] = ['app/**']
    elif mode == 'permissions':
        value['jobs']['container']['permissions'] = {'packages': 'write'}
    elif mode == 'action':
        value['jobs']['static']['steps'][0]['uses'] = 'actions/checkout@main'
    elif mode == 'runner':
        value['jobs']['database']['runs-on'] = 'ubuntu-latest'
    elif mode == 'continue':
        value['jobs']['container']['steps'][0]['continue-on-error'] = True
    elif mode == 'target':
        events['pull_request_target'] = {'branches': ['main']}
    else:
        del value['jobs']['static']['timeout-minutes']
    assert profile_errors(value, profile_map())


def test_checkouts_never_persist_credentials():
    for key, job in workflow()['jobs'].items():
        for step in job.get('steps', []):
            if step.get('uses', '').startswith('actions/checkout@'):
                assert step['with']['persist-credentials'] is False, key


def test_actual_transitional_alias_requires_ci_gate_success():
    gate = workflow()['jobs']['checks']['steps'][0]
    assert gate['env'] == {'CI_GATE_RESULT': '${{ needs.ci-gate.result }}'}
    base = {k: v for k, v in os.environ.items() if k != 'CI_GATE_RESULT'}

    def run(outcome):
        env = base if outcome is None else {**base, 'CI_GATE_RESULT': outcome}
        return subprocess.run(
            ['bash', '-e', '-c', gate['run']], env=env, capture_output=True, check=False
        ).returncode

    assert run('success') == 0
    for outcome in ('failure', 'cancelled', 'skipped', 'pending', '', None):
        assert run(outcome) != 0


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
    assert profile_errors(value, profile_map())


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
    assert profile_errors(value, profile_map())


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
            'cache-binary': False,
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


def test_image_and_workflow_inputs_trigger_their_verifying_jobs():
    profiles = json.loads(Path('.github/ci-profile.json').read_text())['profiles']

    def selected(path):
        return {
            name
            for name, spec in profiles.items()
            if any(glob_to_regex(p).match(path) for p in spec.get('paths', []))
        }

    def jobs(path):
        return {job for name in selected(path) for job in profiles[name]['adds']}

    for copied_into_image in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        assert 'container' in jobs(copied_into_image)
    for workflow_script in (
        'scripts/check_workflows.sh',
        'scripts/ci_identity.py',
        'scripts/ci_profile.py',
    ):
        assert 'workflows' in jobs(workflow_script)
    assert profiles['hotfix']['adds'] == ['all-profiles']


def test_security_job_is_gated_in_base_profile_and_in_the_gate():
    value = workflow()
    job = value['jobs']['security']
    assert job['needs'] == 'classify'
    assert job['permissions'] == {'contents': 'read', 'pull-requests': 'read'}
    assert job['uses'].startswith(
        'gonzalomartinperez/engineering-standards/.github/workflows/security.yml@'
    )
    assert job['with']['dependency-review'] is True
    assert 'LGPL-3.0-only' in job['with']['allow-licenses']
    assert 'security' in value['jobs']['ci-gate']['needs']
    assert 'security' in profile_map()['base']
    mutated = profile_map()
    mutated['base'] = ['secrets']
    assert profile_errors(value, mutated)


def test_buildx_never_caches_its_binary():
    steps = [
        step
        for job in workflow()['jobs'].values()
        for step in job.get('steps', [])
        if step.get('uses', '').startswith('docker/setup-buildx-action@')
    ]
    assert len(steps) == 2
    assert all(step['with']['cache-binary'] is False for step in steps)


@pytest.mark.parametrize('name', ['scorecard', 'vuln-daily'])
def test_scheduled_security_workflows_are_pinned_and_token_less(name):
    path = Path(f'.github/workflows/{name}.yml')
    value = yaml.safe_load(path.read_text())
    assert standalone_errors(name, value) == []
    assert 'pull_request_target' not in value.get('on', value.get(True, {}))
    assert 'ubuntu-latest' not in path.read_text()
    for mutation in (
        lambda v: v.update(permissions={'contents': 'read'}),
        lambda v: v.get('on', v.get(True)).update(pull_request_target={}),
    ):
        broken = deepcopy(value)
        mutation(broken)
        assert standalone_errors(name, broken)
    broken = deepcopy(value)
    job = next(iter(broken['jobs'].values()))
    if 'uses' in job:
        job['uses'] = job['uses'].split('@')[0] + '@main'
    else:
        job['steps'][0]['uses'] = job['steps'][0]['uses'].split('@')[0] + '@v2'
    assert standalone_errors(name, broken)


def test_scorecard_runs_on_main_pushes_weekly_and_manually():
    events = yaml.safe_load(Path('.github/workflows/scorecard.yml').read_text())
    events = events.get('on', events.get(True))
    assert events['push'] == {'branches': ['main']}
    assert events['schedule'] and 'workflow_dispatch' in events
