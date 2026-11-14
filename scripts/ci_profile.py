"""Application-local CI profile; no private operations dependency at execution time."""

import json
import re
from pathlib import Path

import yaml

WORKFLOW_PATH = Path('.github/workflows/ci.yml')
SCORECARD_PATH = Path('.github/workflows/scorecard.yml')
VULN_DAILY_PATH = Path('.github/workflows/vuln-daily.yml')
PROFILE_PATH = Path('.github/ci-profile.json')
NAMES = {
    'classify': 'classify',
    'workflows': 'Workflow validation',
    'secrets': 'Secret scan',
    'security': 'Security checks',
    'static': 'Static checks',
    'database': 'Database tests',
    'container': 'Container verification',
    'ci-gate': 'ci-gate',
    'checks': 'Required checks',
}
# Jobs whose execution classify decides; secrets always runs. `security` is gated but
# belongs to the base profile, so classify always selects it.
GATED = ('workflows', 'security', 'static', 'database', 'container')
# Extra prerequisites that a gated job keeps besides classify.
EXTRA_NEEDS = {
    'workflows': [],
    'security': [],
    'static': [],
    'database': ['static'],
    'container': ['static'],
}
PINNED = re.compile(r'[a-zA-Z0-9._/-]+@([a-f0-9]{40})')
PROFILE_KEYS = {'base', 'required', 'profiles'}
PROFILE_NAMES = {
    'docs',
    'harness',
    'workflow',
    'code',
    'deps-weekly',
    'release',
    'hotfix',
}


def as_list(value) -> list:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def gate_references(condition, key: str) -> bool:
    expected = f"contains(fromJSON(needs.classify.outputs.jobs), '{key}')"
    return isinstance(condition, str) and condition.strip() in (
        expected,
        '${{ ' + expected + ' }}',
    )


def profile_map_errors(jobs: dict, profile_map: dict) -> list[str]:
    errors = []
    if not isinstance(profile_map, dict) or set(profile_map) != PROFILE_KEYS:
        return ['profile map keys']
    if profile_map['required'] != 'ci-gate':
        errors.append('profile map: required check must be ci-gate')
    profiles = profile_map['profiles']
    if not isinstance(profiles, dict) or set(profiles) != PROFILE_NAMES:
        errors.append('profile map: profile inventory')
        profiles = profiles if isinstance(profiles, dict) else {}
    named = as_list(profile_map['base'])
    for spec in profiles.values():
        named += as_list(spec.get('adds'))
    for name in named:
        if name != 'all-profiles' and name not in jobs:
            errors.append(f'profile map: unknown job {name}')
    for name in ('deps-weekly', 'release', 'hotfix'):
        if 'all-profiles' not in as_list(profiles.get(name, {}).get('adds')):
            errors.append(f'profile map: {name} must run every profile')
    for name in ('secrets', 'security'):
        if name not in as_list(profile_map['base']):
            errors.append(f'profile map: {name} must always run')
    return errors


def profile_errors(workflow: dict, profile_map: dict) -> list[str]:
    errors = []
    events = workflow.get('on', workflow.get(True, {}))
    if workflow.get('name') != 'CI':
        errors.append('workflow name')
    for event in ('pull_request', 'push'):
        expected = {'branches': ['develop', 'main']}
        if event == 'pull_request':
            expected['types'] = [
                'opened',
                'synchronize',
                'reopened',
                'edited',
                'ready_for_review',
                'labeled',
                'unlabeled',
            ]
        if events.get(event) != expected:
            errors.append('required events cannot be filtered')
    if workflow.get('permissions') != {'contents': 'read'}:
        errors.append('default token permissions')
    if workflow.get('concurrency', {}).get('cancel-in-progress') is not True:
        errors.append('stale candidate concurrency')
    jobs = workflow.get('jobs', {})
    if set(jobs) != set(NAMES):
        errors.append('exact job inventory')
    for key, name in NAMES.items():
        job = jobs.get(key, {})
        reusable = 'uses' in job
        if job.get('name') != name:
            errors.append(f'{key}: name')
        if job.get('continue-on-error'):
            errors.append(f'{key}: required work cannot be skipped')
        if not reusable and job.get('runs-on') != 'ubuntu-24.04':
            errors.append(f'{key}: isolated hosted runner')
        if not reusable and not isinstance(job.get('timeout-minutes'), int):
            errors.append(f'{key}: timeout')
        if reusable and not PINNED.fullmatch(job['uses']):
            errors.append(f'{key}: unpinned reusable workflow')
        permissions = job.get('permissions', workflow.get('permissions', {}))
        if any(value != 'read' for value in permissions.values()):
            errors.append(f'{key}: elevated permissions')
        if key == 'container' and job.get('defaults', {}).get('run', {}).get(
            'shell'
        ) not in (None, 'bash'):
            errors.append('container: scan pipelines cannot override bash pipefail')
        for step in job.get('steps', []):
            if key == 'container' and step.get('shell') not in (None, 'bash'):
                errors.append('container: scan steps cannot override bash pipefail')
            if step.get('continue-on-error'):
                errors.append(f'{key}: step failure hidden')
            if 'uses' in step and not PINNED.fullmatch(step['uses']):
                errors.append(f'{key}: unpinned action')
    if 'pull_request_target' in events:
        errors.append('pull_request_target is forbidden')
    for key in GATED:
        job = jobs.get(key, {})
        needs = as_list(job.get('needs'))
        if sorted(needs) != sorted(['classify', *EXTRA_NEEDS[key]]):
            errors.append(f'{key}: dependency graph')
        if not gate_references(job.get('if'), key):
            errors.append(f'{key}: must be gated on its own id in classify jobs')
    if jobs.get('secrets', {}).get('if') or as_list(
        jobs.get('secrets', {}).get('needs')
    ):
        errors.append('secrets: must run unconditionally')
    if jobs.get('classify', {}).get('needs') or jobs.get('classify', {}).get('if'):
        errors.append('classify: must be the unconditional root job')
    gate = jobs.get('ci-gate', {})
    if (
        gate.get('if') not in ('always()', '${{ always() }}')
        or gate.get('permissions') != {}
    ):
        errors.append('ci-gate: must always run without permissions')
    if sorted(as_list(gate.get('needs'))) != sorted(
        key for key in jobs if key not in ('checks', 'ci-gate')
    ):
        errors.append('ci-gate: must need every other job except checks')
    if 'ci-gate' in as_list(gate.get('needs')):
        errors.append('ci-gate: cannot need itself')
    gate_steps = gate.get('steps', [])
    gate_uses = gate_steps[0].get('uses', '') if len(gate_steps) == 1 else ''
    if not gate_uses.startswith(
        'gonzalomartinperez/engineering-standards/actions/ci-gate@'
    ) or gate_steps[0].get('with') != {
        'needs': '${{ toJSON(needs) }}',
        'expected': '${{ needs.classify.outputs.jobs }}',
    }:
        errors.append('ci-gate: single shared action step with needs and expected')
    classify_pin = PINNED.fullmatch(jobs.get('classify', {}).get('uses', ''))
    gate_pin = PINNED.fullmatch(gate_uses)
    if not classify_pin or not gate_pin or classify_pin[1] != gate_pin[1]:
        errors.append('classify and ci-gate must pin the same shared SHA')
    checks = jobs.get('checks', {})
    check_steps = checks.get('steps', [])
    if (
        checks.get('if') not in ('always()', '${{ always() }}')
        or checks.get('permissions') != {}
        or as_list(checks.get('needs')) != ['ci-gate']
    ):
        errors.append(
            'checks: transitional alias must always run and need only ci-gate'
        )
    if (
        len(check_steps) != 1
        or check_steps[0].get('env')
        != {'CI_GATE_RESULT': '${{ needs.ci-gate.result }}'}
        or '${{' in check_steps[0].get('run', '')
        or 'CI_GATE_RESULT' not in check_steps[0].get('run', '')
    ):
        errors.append('checks: must inspect only the ci-gate result through env')
    required = {
        'workflows': 'scripts/check_workflows.sh',
        'secrets': 'scripts.scan_secrets',
        'static': "pytest -q -m 'not integration'",
        'database': 'pytest -q -m integration',
        'container': 'scripts.container_smoke',
    }
    for key, command in required.items():
        if not any(
            command in step.get('run', '')
            for step in jobs.get(key, {}).get('steps', [])
        ):
            errors.append(f'{key}: meaningful application verification absent')
    database_scans = [
        step.get('run', '')
        for step in jobs.get('container', {}).get('steps', [])
        if step.get('name')
        == 'Inventory PostgreSQL and reject critical or fixable high findings'
    ]
    if (
        len(database_scans) != 1
        or any(
            command not in database_scans[0]
            for command in (
                '--list-all-pkgs',
                '--output artifacts/postgres-vulnerabilities.json portfolio-assistant-postgres:18.6',
                'python -m scripts.image_security',
                '--report artifacts/postgres-vulnerabilities.json --image-id "$image_id"',
                '| tee artifacts/postgres-security-summary.json',
            )
        )
        or any(
            bypass in database_scans[0]
            for bypass in (
                '--ignore-unfixed',
                '--severity ',
                '|| true',
                'fixable_critical',
            )
        )
    ):
        errors.append(
            'container: complete PostgreSQL inventory and all-critical gate required'
        )
    if workflow.get('defaults', {}).get('run', {}).get('shell') != 'bash':
        errors.append('runtime gates require the explicit bash pipefail shell')
    errors += profile_map_errors(jobs, profile_map)
    return errors


def standalone_errors(name: str, workflow: dict) -> list[str]:
    """Scheduled security workflows: pinned, token-less by default, never privileged triggers."""
    errors = []
    events = workflow.get('on', workflow.get(True, {}))
    if workflow.get('name') != name:
        errors.append(f'{name}: workflow name')
    if workflow.get('permissions') != {}:
        errors.append(f'{name}: top-level permissions must be empty')
    if 'pull_request_target' in events or 'pull_request' in events:
        errors.append(f'{name}: no pull request triggers')
    if 'schedule' not in events or 'workflow_dispatch' not in events:
        errors.append(f'{name}: schedule and manual dispatch required')
    for key, job in workflow.get('jobs', {}).items():
        if 'uses' in job and not PINNED.fullmatch(job['uses']):
            errors.append(f'{name}.{key}: unpinned reusable workflow')
        if 'uses' not in job and job.get('runs-on') != 'ubuntu-24.04':
            errors.append(f'{name}.{key}: isolated hosted runner')
        if not isinstance(job.get('permissions'), dict):
            errors.append(f'{name}.{key}: explicit job permissions')
        for step in job.get('steps', []):
            if 'uses' in step and not PINNED.fullmatch(step['uses']):
                errors.append(f'{name}.{key}: unpinned action')
            if step.get('continue-on-error'):
                errors.append(f'{name}.{key}: step failure hidden')
    return errors


def main():
    errors = profile_errors(
        yaml.safe_load(WORKFLOW_PATH.read_text()),
        json.loads(PROFILE_PATH.read_text()),
    )
    errors += standalone_errors('scorecard', yaml.safe_load(SCORECARD_PATH.read_text()))
    errors += standalone_errors(
        'vuln-daily', yaml.safe_load(VULN_DAILY_PATH.read_text())
    )
    if errors:
        raise SystemExit('\n'.join(errors))
    print('API CI profile: dynamic jobs, ci-gate, trust and dependencies verified.')


if __name__ == '__main__':
    main()
