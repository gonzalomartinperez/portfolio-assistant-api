"""Authorization and whole-resolution decisions for dependency maintenance."""

import copy
import json
from pathlib import Path

import pytest

from scripts.dependabot_automation import current_candidate, hold_check, process
from scripts.dependabot_policy import (
    ACTIONS_ID,
    BOT_ID,
    POLICY_CHECK,
    REPOSITORY,
    Decision,
    allowed_version,
    candidate,
    checks_passed,
    dependency_changes,
    protected_for_automation,
)

HEAD = 'a' * 40
BASE = 'b' * 40
BOT = {'login': 'dependabot[bot]', 'id': BOT_ID, 'type': 'Bot'}


def pull_request():
    return {
        'number': 1,
        'node_id': 'PR_fixture',
        'state': 'open',
        'draft': False,
        'user': BOT.copy(),
        'labels': [],
        'commits': 1,
        'changed_files': 1,
        'base': {'ref': 'develop', 'sha': BASE, 'repo': {'full_name': REPOSITORY}},
        'head': {'sha': HEAD, 'repo': {'full_name': REPOSITORY}},
        'mergeable': True,
        'auto_merge': None,
    }


def commit():
    return {
        'sha': HEAD,
        'author': BOT.copy(),
        'committer': {'id': 19864447},
        'commit': {'verification': {'verified': True}},
    }


def repository():
    return {
        'autoMergeAllowed': True,
        'ref': {
            'target': {'oid': BASE},
            'branchProtectionRule': {
                'isAdminEnforced': True,
                'requiresStatusChecks': True,
                'requiresStrictStatusChecks': True,
                'allowsForcePushes': False,
                'allowsDeletions': False,
                'requiredStatusChecks': [
                    {'context': name, 'app': {'databaseId': ACTIONS_ID}}
                    for name in ('checks', POLICY_CHECK)
                ],
            },
        },
    }


def required_checks():
    return repository()['ref']['branchProtectionRule']['requiredStatusChecks']


def successful_check():
    return {
        'name': 'checks',
        'status': 'completed',
        'conclusion': 'success',
        'head_sha': HEAD,
        'app': {'id': ACTIONS_ID},
    }


def snapshot(pytest_version='9.1.1', ini_version='2.3.0', minimum='9.1.1'):
    manifest = f"""[project]
name = "sample"
dependencies = ["fastapi>=0.141.1"]
[dependency-groups]
dev = ["pytest>={minimum}"]
"""
    lock = f"""version = 1
revision = 3
requires-python = "==3.13.*"
[[package]]
name = "sample"
version = "0.1.0"
source = {{ virtual = "." }}
dependencies = [{{ name = "fastapi" }}]
[package.metadata.requires-dev]
dev = [{{ name = "pytest", specifier = ">={minimum}" }}]
[[package]]
name = "fastapi"
version = "0.141.1"
source = {{ registry = "https://pypi.org/simple" }}
"""
    for name, version in (('pytest', pytest_version), ('iniconfig', ini_version)):
        lock += f'''[[package]]
name = "{name}"
version = "{version}"
source = {{ registry = "https://pypi.org/simple" }}
sdist = {{ url = "https://files.pythonhosted.org/packages/{name}-{version}.tar.gz", hash = "sha256:{'a' * 64}", size = 100 }}
wheels = [{{ url = "https://files.pythonhosted.org/packages/{name}-{version}-py3-none-any.whl", hash = "sha256:{'b' * 64}", size = 100 }}]
'''
    return {'pyproject.toml': manifest, 'uv.lock': lock}


@pytest.mark.parametrize(
    ('name', 'before', 'after', 'eligible'),
    [
        ('pytest', '9.1.1', '9.1.2', True),
        ('iniconfig', '2.3.0', '2.4.0', True),
        ('pytest', '9.1.1', '9.2.0', False),
        ('pytest', '9.1.1', '10.0.0', False),
        ('pytest', '9.1.1', '9.1.2rc1', False),
        ('pytest', '0.1.1', '0.1.2', False),
        ('pytest', '9.1.1', '9.1.1.post1', False),
        ('pytest', '9.1.1', 'unknown', False),
        ('pytest', '9.1.1', '9.1.0', False),
        ('openai', '3.19.2', '3.19.3', False),
    ],
)
def test_explicit_version_policy(name, before, after, eligible):
    assert allowed_version(name, before, after) is eligible


def test_lock_only_and_manifest_updates_validate_the_whole_resolution():
    before = snapshot()
    assert dependency_changes(before, snapshot('9.1.2')).eligible
    assert dependency_changes(before, snapshot('9.1.2', minimum='9.1.2')).eligible
    assert dependency_changes(before, snapshot(ini_version='2.4.0')).eligible
    assert dependency_changes(before, snapshot('9.1.2', '2.4.0')).updates == (
        'iniconfig',
        'pytest',
    )
    assert not dependency_changes(before, snapshot('9.1.2', '3.0.0')).eligible
    assert not dependency_changes(before, snapshot(minimum='9.1.2')).eligible
    assert not dependency_changes(before, before).eligible


@pytest.mark.parametrize(
    'mutation',
    [
        'manifest_script',
        'runtime',
        'registry',
        'artifact_host',
        'artifact_hash',
        'dependency_edge',
        'python',
        'new_package',
        'duplicate_package',
        'bad_toml',
    ],
)
def test_unexpected_semantics_cannot_hide_in_allowed_files(mutation):
    before, after = snapshot(), snapshot('9.1.2')
    if mutation == 'manifest_script':
        after['pyproject.toml'] += '\n[project.scripts]\nunsafe = "arbitrary:main"\n'
    elif mutation == 'runtime':
        after['uv.lock'] = after['uv.lock'].replace('0.141.1', '0.141.2')
    elif mutation == 'registry':
        after['uv.lock'] = after['uv.lock'].replace(
            'pypi.org/simple', 'untrusted.example/simple'
        )
    elif mutation == 'artifact_host':
        after['uv.lock'] = after['uv.lock'].replace(
            'files.pythonhosted.org', 'untrusted.example'
        )
    elif mutation == 'artifact_hash':
        after['uv.lock'] = after['uv.lock'].replace('sha256:', 'md5:')
    elif mutation == 'dependency_edge':
        after['uv.lock'] = after['uv.lock'].replace(
            'name = "pytest"\n',
            'name = "pytest"\ndependencies = [{ name = "fastapi" }]\n',
        )
    elif mutation == 'python':
        after['uv.lock'] = after['uv.lock'].replace('3.13.*', '3.14.*')
    elif mutation in ('new_package', 'duplicate_package'):
        name = 'unknown' if mutation == 'new_package' else 'pytest'
        after['uv.lock'] += f'[[package]]\nname = "{name}"\nversion = "1.0.0"\n'
    else:
        after['uv.lock'] = 'not TOML'
    assert not dependency_changes(before, after).eligible


def test_approved_package_becoming_runtime_is_manual():
    before, after = snapshot(), snapshot('9.1.2')
    for value in (before, after):
        value['uv.lock'] = value['uv.lock'].replace(
            'dependencies = [{ name = "fastapi" }]',
            'dependencies = [{ name = "pytest" }]',
        )
    assert not dependency_changes(before, after).eligible


@pytest.mark.parametrize(
    'mutation',
    [
        'spoof',
        'main',
        'fork',
        'human_commit',
        'unsigned',
        'missing_commit',
        'new_head',
        'workflow',
        'script',
        'renamed',
        'missing_file',
        'manual_label',
    ],
)
def test_identity_revision_and_all_changed_files_are_authorization_inputs(mutation):
    pr, commits = pull_request(), [commit()]
    files = [{'filename': 'uv.lock', 'status': 'modified'}]
    assert candidate(pr, commits, files).eligible
    if mutation == 'spoof':
        pr['title'] = 'Bump pytest by Dependabot'
        pr['labels'] = [{'name': 'dependencies'}]
        pr['user'] = {'login': 'dependabot[bot]', 'id': 123, 'type': 'User'}
    elif mutation == 'main':
        pr['base']['ref'] = 'main'
    elif mutation == 'fork':
        pr['head']['repo']['full_name'] = 'attacker/portfolio-assistant-api'
    elif mutation == 'human_commit':
        commits[0]['author'] = {'login': 'maintainer', 'id': 123, 'type': 'User'}
    elif mutation == 'unsigned':
        commits[0]['commit']['verification']['verified'] = False
    elif mutation == 'missing_commit':
        pr['commits'] = 2
    elif mutation == 'new_head':
        pr['head']['sha'] = 'c' * 40
    elif mutation == 'workflow':
        files[0]['filename'] = '.github/workflows/quality.yml'
    elif mutation == 'script':
        files[0]['filename'] = 'scripts/dependabot_policy.py'
    elif mutation == 'renamed':
        files[0]['status'] = 'renamed'
    elif mutation == 'missing_file':
        pr['changed_files'] = 2
    else:
        pr['labels'] = [{'name': 'dependencies:manual'}]
    assert not candidate(pr, commits, files).eligible


@pytest.mark.parametrize(
    'conclusion', ['failure', 'cancelled', 'timed_out', 'neutral', None]
)
def test_unsuccessful_required_checks_never_arm_auto_merge(conclusion):
    check = successful_check()
    check['conclusion'] = conclusion
    assert not checks_passed([check], required_checks(), HEAD)


def test_missing_pending_foreign_stale_and_duplicate_checks_fail_closed():
    check = successful_check()
    assert checks_passed([check], required_checks(), HEAD)
    assert not checks_passed([], required_checks(), HEAD)
    assert not checks_passed([check], [], HEAD)
    assert not checks_passed([check, check], required_checks(), HEAD)
    for key, value in [
        ('status', 'in_progress'),
        ('head_sha', BASE),
        ('app', {'id': 1}),
    ]:
        modified = {**check, key: value}
        assert not checks_passed([modified], required_checks(), HEAD)


def test_strict_pinned_policy_check_is_an_activation_prerequisite():
    data = repository()
    assert protected_for_automation(data)
    for name in (
        'requiresStrictStatusChecks',
        'isAdminEnforced',
        'requiresStatusChecks',
    ):
        changed = copy.deepcopy(data)
        changed['ref']['branchProtectionRule'][name] = False
        assert not protected_for_automation(changed)
    changed = copy.deepcopy(data)
    changed['ref']['branchProtectionRule']['requiredStatusChecks'].pop()
    assert not protected_for_automation(changed)
    data['autoMergeAllowed'] = False
    assert not protected_for_automation(data)


@pytest.mark.parametrize(
    'mutation',
    ['new_head', 'advanced_base', 'main', 'conflict', 'unknown_mergeable', 'opt_out'],
)
def test_recheck_invalidates_racing_changes(mutation):
    pr, fresh = pull_request(), pull_request()
    assert current_candidate(pr, fresh, BASE)
    if mutation == 'new_head':
        fresh['head']['sha'] = 'c' * 40
    elif mutation == 'advanced_base':
        fresh['base']['sha'] = 'c' * 40
    elif mutation == 'main':
        fresh['base']['ref'] = 'main'
    elif mutation in ('conflict', 'unknown_mergeable'):
        fresh['mergeable'] = False if mutation == 'conflict' else None
    else:
        fresh['labels'] = [{'name': 'dependencies:manual'}]
    assert not current_candidate(pr, fresh, BASE)


def test_native_merge_is_armed_under_a_required_hold_then_released(monkeypatch):
    """Exercise sequencing, including stale/failed checks and revoking previous intent."""
    import scripts.dependabot_automation as automation

    events = []
    pr = pull_request()
    pr['auto_merge'] = {'enabled_by': BOT}
    check = successful_check()

    class API:
        def request(self, path):
            if '/pulls/' in path:
                return copy.deepcopy(pr)
            if '/check-runs' in path:
                return {'total_count': 1, 'check_runs': [check]}
            if '/compare/' in path:
                return {'merge_base_commit': {'sha': BASE}}
            raise AssertionError(path)

    monkeypatch.setenv('DEPENDABOT_AUTOMERGE_ENABLED', 'true')
    monkeypatch.setattr(
        automation,
        'hold_check',
        lambda api, pr, manual=False: (events.append('hold') or 1, manual),
    )
    monkeypatch.setattr(
        automation,
        'change_auto_merge',
        lambda api, pr, enable: events.append('arm' if enable else 'revoke'),
    )
    monkeypatch.setattr(
        automation,
        'finish_check',
        lambda api, check, conclusion, reason: events.append(conclusion),
    )
    monkeypatch.setattr(automation, 'controls', lambda api: repository())
    monkeypatch.setattr(
        automation, 'inspect_candidate', lambda api, pr: Decision(True, 'approved')
    )
    assert process(API(), 1, HEAD) == 'native_auto_merge_enabled'
    assert events == ['hold', 'revoke', 'arm', 'success']
    events.clear()
    assert process(API(), 1, BASE) == 'stale_event'
    assert events == []
    monkeypatch.setattr(
        automation, 'inspect_candidate', lambda api, pr: Decision(False, 'human_commit')
    )
    assert process(API(), 1, HEAD) == 'human_commit'
    assert events == ['hold', 'revoke', 'action_required']
    events.clear()
    assert process(API(), 1, HEAD, manual=True) == 'manual_review'
    assert events == ['hold', 'revoke', 'success']
    events.clear()
    monkeypatch.setattr(
        automation, 'inspect_candidate', lambda api, pr: Decision(True, 'approved')
    )
    check['conclusion'] = 'failure'
    assert process(API(), 1, HEAD) == 'waiting_for_required_checks'
    assert events == ['hold', 'revoke', 'action_required']
    events.clear()

    def denied_controls(api):
        raise automation.GitHubRequestError('graphql; HTTP 403', permission_denied=True)

    monkeypatch.setattr(automation, 'controls', denied_controls)
    with pytest.raises(automation.GitHubRequestError):
        process(API(), 1, HEAD)
    assert events == ['hold', 'revoke']


def test_manual_choice_survives_quality_completion_and_a_failed_prior_attempt(
    monkeypatch,
):
    import scripts.dependabot_automation as automation

    pr = pull_request()
    events = []

    class API:
        def __init__(self):
            self.checks = []

        def request(self, path, method='GET', data=None):
            if '/pulls/' in path:
                return copy.deepcopy(pr)
            if method == 'GET' and '/check-runs' in path:
                return {'total_count': len(self.checks), 'check_runs': self.checks}
            if method == 'POST':
                self.checks.append({**data, 'id': 1, 'app': {'id': ACTIONS_ID}})
                return self.checks[0]
            if method == 'PATCH':
                self.checks[0].update(data)
                return self.checks[0]
            raise AssertionError(path)

    api = API()
    assert hold_check(api, pr, manual=True) == (1, True)
    # A process dying while the check is held must not erase the human's choice.
    assert hold_check(api, pr) == (1, True)
    monkeypatch.setenv('DEPENDABOT_AUTOMERGE_ENABLED', 'true')
    monkeypatch.setattr(
        automation, 'change_auto_merge', lambda api, pr, enable: events.append(enable)
    )
    # Simulate the later Quality-completion event, not another manual invocation.
    assert process(api, 1, HEAD) == 'manual_review'
    assert events == [False]
    assert api.checks[0]['conclusion'] == 'success'
    assert api.checks[0]['external_id'].endswith(':manual')


def test_privileged_workflow_never_checks_out_or_executes_pr_code():
    import yaml

    workflow = yaml.safe_load(
        Path('.github/workflows/dependabot-policy.yml').read_text()
    )
    job = workflow['jobs']['policy']
    checkout, policy = job['steps']
    assert checkout['with']['ref'] == '${{ github.workflow_sha }}'
    assert checkout['with']['persist-credentials'] is False
    assert policy['run'] == 'python3 -m scripts.dependabot_automation'
    assert 'pull_request.head' not in json.dumps(job)
    assert workflow['permissions'] == {}
    assert job['permissions'] == {
        'contents': 'write',
        'pull-requests': 'write',
        'checks': 'write',
    }


def test_api_failure_diagnostics_never_include_remote_text(monkeypatch):
    import subprocess

    from scripts.dependabot_automation import GitHub, GitHubRequestError

    monkeypatch.setattr(
        subprocess,
        'run',
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout='private-sentinel', stderr='private-sentinel (HTTP 403)'
        ),
    )
    with pytest.raises(GitHubRequestError) as failure:
        GitHub().request('graphql', 'POST', {'query': 'trusted query'})
    assert str(failure.value) == 'graphql; HTTP 403'
    assert 'private-sentinel' not in str(failure.value)


def test_read_only_audit_reports_permission_blocker_without_authorizing_merge(
    monkeypatch, capsys
):
    import sys

    import scripts.dependabot_automation as automation

    class API:
        def request(self, path, method='GET', data=None):
            assert method == 'GET' and '/pulls/' in path
            return pull_request()

    def denied(api):
        raise automation.GitHubRequestError('graphql; HTTP 403', permission_denied=True)

    monkeypatch.setattr(sys, 'argv', ['policy', '--audit-pr', '1'])
    monkeypatch.setattr(automation, 'GitHub', API)
    monkeypatch.setattr(automation, 'controls', denied)
    automation.main()
    report = json.loads(capsys.readouterr().out)
    assert report['audit_state'] == 'permission_blocked'
    assert report['eligible'] is False and report['protections_ready'] is False
