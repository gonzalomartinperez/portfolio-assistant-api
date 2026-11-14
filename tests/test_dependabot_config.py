"""Weekly single-PR rule: static checks of the Dependabot config and the guard workflow."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / '.github/dependabot.yml').read_text())
GUARD = yaml.safe_load((ROOT / '.github/workflows/deps-weekly-guard.yml').read_text())
GROUP_ONLY_KEYS = (
    'open-pull-requests-limit',
    'commit-message',
    'schedule',
    'target-branch',
)


def _directories(entry):
    return set(entry.get('directories') or [entry['directory']])


def test_single_weekly_group_carries_the_rule():
    groups = CONFIG['multi-ecosystem-groups']
    assert list(groups) == ['weekly']
    group = groups['weekly']
    assert group['schedule'] == {
        'interval': 'weekly',
        'day': 'monday',
        'time': '09:00',
        'timezone': 'America/Argentina/Buenos_Aires',
    }
    assert group['target-branch'] == 'develop'
    assert group['open-pull-requests-limit'] == 1
    assert group['commit-message'] == {'prefix': 'chore(deps)'}
    assert group['labels'] == ['dependencies']


def test_every_entry_joins_the_group_without_group_only_keys():
    for entry in CONFIG['updates']:
        assert entry['multi-ecosystem-group'] == 'weekly'
        assert entry['patterns'] == ['*']
        for key in GROUP_ONLY_KEYS:
            assert key not in entry, (entry['package-ecosystem'], key)


def test_ecosystems_and_semver_cooldowns():
    entries = CONFIG['updates']
    assert sorted(e['package-ecosystem'] for e in entries) == [
        'docker',
        'github-actions',
        'uv',
    ]
    for entry in entries:
        cooldown = entry['cooldown']
        assert cooldown['default-days'] == 7
        semver = {k for k in cooldown if k.startswith('semver-')}
        if entry['package-ecosystem'] == 'uv':
            assert cooldown == {
                'default-days': 7,
                'semver-major-days': 14,
                'semver-patch-days': 3,
            }
        else:
            assert not semver, entry['package-ecosystem']


def test_every_dockerfile_and_compose_directory_is_covered():
    by_eco = {}
    for entry in CONFIG['updates']:
        by_eco.setdefault(entry['package-ecosystem'], set()).update(_directories(entry))
    skip = {'.venv', '.git', 'node_modules'}

    def found(pattern):
        return {
            '/' + path.parent.relative_to(ROOT).as_posix()
            if path.parent != ROOT
            else '/'
            for path in ROOT.rglob(pattern)
            if not skip & set(path.relative_to(ROOT).parts)
        }

    dockerfiles = found('Dockerfile') | found('Dockerfile.*')
    dockerfiles = {d for d in dockerfiles if d != '/infra'}
    assert dockerfiles and dockerfiles <= by_eco['docker']
    # Dependabot's docker-compose fetcher only reads files matching this pattern; none
    # exists today, so the ecosystem is absent (ADR019). Adding one requires an entry.
    parseable = re.compile(
        r'(docker-)?compose(-[\w]+)?(?>\.[\w-]+)?\.ya?ml', re.IGNORECASE
    )
    compose_files = [
        path
        for path in ROOT.rglob('*.y*ml')
        if parseable.fullmatch(path.name) and not {'.git', '.venv'} & set(path.parts)
    ]
    assert not compose_files or 'docker-compose' in by_eco


def test_guard_workflow_pins_shared_workflow_by_sha_with_no_default_permissions():
    assert GUARD['permissions'] == {}
    uses = GUARD['jobs']['guard']['uses']
    assert re.fullmatch(
        r'gonzalomartinperez/engineering-standards/\.github/workflows/deps-weekly-guard\.yml@[0-9a-f]{40}',
        uses,
    )


def test_guard_runs_only_for_dependabot_prs_or_schedule_with_minimal_permissions():
    job = GUARD['jobs']['guard']
    assert job['if'] == (
        "github.event_name != 'pull_request' || github.actor == 'dependabot[bot]'"
    )
    assert job['permissions'] == {
        'contents': 'read',
        'pull-requests': 'write',
        'issues': 'write',
        'checks': 'read',
    }
