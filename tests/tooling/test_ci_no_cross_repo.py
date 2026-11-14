"""Pull request CI reads no other repository (ADR016)."""

from pathlib import Path

import yaml

CI = Path('.github/workflows/ci.yml')
CROSS = Path('.github/workflows/cross-repo.yml')


def test_ci_has_no_cross_repository_checkout():
    assert 'repository: gonzalomartinperez/' not in CI.read_text()
    workflow = yaml.safe_load(CI.read_text())
    for job in workflow['jobs'].values():
        for step in job.get('steps', []):
            assert 'repository' not in step.get('with', {})


def test_ci_indexes_the_frozen_snapshot():
    text = CI.read_text()
    assert text.count('--source snapshot --repo evals/corpus') == 2
    assert 'public-portfolio' not in text


def test_cross_repo_workflow_is_scheduled_pinned_and_least_privilege():
    workflow = yaml.safe_load(CROSS.read_text())
    triggers = workflow['on']
    assert triggers['schedule'] == [{'cron': '0 6 * * *'}]
    assert 'frontend_commit' in triggers['workflow_dispatch']['inputs']
    assert workflow['permissions'] == {'contents': 'read'}
    for job in workflow['jobs'].values():
        for step in job['steps']:
            if 'uses' in step:
                ref = step['uses'].split('@', 1)[1].split()[0]
                assert len(ref) == 40, step['uses']
            if step.get('uses', '').startswith('actions/checkout'):
                assert step['with']['persist-credentials'] is False
