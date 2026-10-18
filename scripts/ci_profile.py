"""Application-local CI profile; no private operations dependency at execution time."""

import re
from pathlib import Path

import yaml

NAMES = {
    'workflows': 'Workflow validation',
    'secrets': 'Secret scan',
    'static': 'Static checks',
    'database': 'Database tests',
    'container': 'Container verification',
    'checks': 'Required checks',
}
NEEDS = {
    'workflows': [],
    'secrets': [],
    'static': [],
    'database': ['static'],
    'container': ['static'],
    'checks': ['workflows', 'secrets', 'static', 'database', 'container'],
}


def profile_errors(workflow: dict) -> list[str]:
    errors = []
    events = workflow.get('on', workflow.get(True, {}))
    if workflow.get('name') != 'Quality':
        errors.append('workflow name')
    for event in ('pull_request', 'push'):
        if events.get(event) != {'branches': ['develop', 'main']}:
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
        needs = job.get('needs', [])
        if isinstance(needs, str):
            needs = [needs]
        if job.get('name') != name or needs != NEEDS[key]:
            errors.append(f'{key}: name/dependency graph')
        if job.get('continue-on-error') or (key != 'checks' and job.get('if')):
            errors.append(f'{key}: required work cannot be skipped')
        if job.get('runs-on') not in ('ubuntu-latest', 'ubuntu-24.04'):
            errors.append(f'{key}: isolated hosted runner')
        permissions = job.get('permissions', workflow.get('permissions', {}))
        if any(value != 'read' for value in permissions.values()):
            errors.append(f'{key}: elevated permissions')
        for step in job.get('steps', []):
            if step.get('continue-on-error'):
                errors.append(f'{key}: step failure hidden')
            if 'uses' in step and not re.fullmatch(
                r'[a-zA-Z0-9._/-]+@[a-f0-9]{40}', step['uses']
            ):
                errors.append(f'{key}: unpinned action')
    gate = jobs.get('checks', {})
    steps = gate.get('steps', [])
    expected_env = {
        key.upper() + '_RESULT': '${{ needs.' + key + '.result }}'
        for key in NEEDS['checks']
    }
    if (
        gate.get('if') not in ('always()', '${{ always() }}')
        or gate.get('permissions') != {}
    ):
        errors.append('aggregate must always run without permissions')
    if len(steps) != 1 or steps[0].get('env') != expected_env:
        errors.append('aggregate must inspect every expected job')
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
    return errors


def main():
    errors = profile_errors(
        yaml.safe_load(Path('.github/workflows/quality.yml').read_text())
    )
    if errors:
        raise SystemExit('\n'.join(errors))
    print('Paired API CI profile: exact jobs, trust and dependencies verified.')


if __name__ == '__main__':
    main()
