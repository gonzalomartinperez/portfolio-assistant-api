"""Release metadata, release workflow and community files (engineering-standards ADR 0003, OD-78)."""

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / '.github' / 'workflows'


def project_version() -> str:
    with (ROOT / 'pyproject.toml').open('rb') as handle:
        return str(tomllib.load(handle)['project']['version'])


def release_notes_script() -> str:
    workflow = yaml.safe_load((WORKFLOWS / 'release.yml').read_text())
    steps = workflow['jobs']['release']['steps']
    step = next(s for s in steps if s.get('name') == 'Read version and release notes')
    assert step['shell'] == 'python'
    return str(step['run'])


def run_notes(tmp_path: Path, version: str, changelog: str) -> tuple[str, str | None]:
    (tmp_path / 'pyproject.toml').write_text(
        f'[project]\nname = "x"\nversion = "{version}"\n'
    )
    (tmp_path / 'CHANGELOG.md').write_text(changelog)
    script = tmp_path / 'notes.py'
    script.write_text(release_notes_script())
    output = tmp_path / 'out'
    env = {**os.environ, 'GITHUB_OUTPUT': str(output), 'RUNNER_TEMP': str(tmp_path)}
    subprocess.run(
        [sys.executable, '-I', str(script)], cwd=tmp_path, env=env, check=True
    )
    notes = tmp_path / 'notes.md'
    return output.read_text(), notes.read_text() if notes.exists() else None


def test_current_version_has_a_dated_changelog_section():
    version = project_version()
    assert re.fullmatch(r'\d+\.\d+\.\d+', version)
    changelog = (ROOT / 'CHANGELOG.md').read_text()
    assert '## [Unreleased]' in changelog
    assert re.search(
        rf'(?m)^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$', changelog
    )


def test_release_notes_stop_at_the_next_section_and_link_references(tmp_path):
    changelog = (
        '# Changelog\n\n## [Unreleased]\n\n## [1.2.3] - 2026-01-01\n\n### Added\n\n- new\n\n'
        '## [1.2.2] - 2025-12-01\n\n- old\n\n[1.2.3]: https://example.test\n'
    )
    output, notes = run_notes(tmp_path, '1.2.3', changelog)
    assert 'version=1.2.3' in output
    assert 'has_section=true' in output
    assert notes is not None
    assert '- new' in notes
    assert 'old' not in notes
    assert 'example.test' not in notes


def test_release_notes_report_a_missing_section(tmp_path):
    output, notes = run_notes(
        tmp_path, '2.0.0', '# Changelog\n\n## [Unreleased]\n\n- pending\n'
    )
    assert 'has_section=false' in output
    assert notes is None


def test_release_workflow_runs_only_on_main_with_least_privilege():
    workflow = yaml.safe_load((WORKFLOWS / 'release.yml').read_text())
    triggers = workflow[True]  # PyYAML reads the `on` key as boolean True
    assert triggers == {'push': {'branches': ['main']}}
    assert workflow['permissions'] == {}
    job = workflow['jobs']['release']
    assert job['permissions'] == {'contents': 'write'}
    checkout = next(
        s
        for s in job['steps']
        if str(s.get('uses', '')).startswith('actions/checkout@')
    )
    assert checkout['with']['persist-credentials'] is False


def test_standards_workflows_use_the_locked_commit():
    lock = json.loads((ROOT / 'standards.lock').read_text())['standards']
    commit = lock['commit']
    assert re.fullmatch(r'[0-9a-f]{40}', commit)
    pins = set()
    for path in WORKFLOWS.glob('*.yml'):
        pins.update(
            re.findall(
                r'gonzalomartinperez/engineering-standards/\S+@([0-9a-f]{40})',
                path.read_text(),
            )
        )
    assert pins == {commit}
    drift = yaml.safe_load((WORKFLOWS / 'drift.yml').read_text())
    assert drift['jobs']['drift']['permissions'] == {'contents': 'read'}


def test_community_files_follow_the_standard():
    for name in (
        'SECURITY.md',
        'SUPPORT.md',
        'CODE_OF_CONDUCT.md',
        'CHANGELOG.md',
        'LICENSE',
    ):
        assert (ROOT / name).is_file(), name
    templates = ROOT / '.github' / 'ISSUE_TEMPLATE'
    assert sorted(p.name for p in templates.iterdir()) == [
        'bug.yml',
        'config.yml',
        'feature.yml',
    ]
    assert (
        yaml.safe_load((templates / 'config.yml').read_text())['blank_issues_enabled']
        is False
    )
    assert (ROOT / '.github' / 'PULL_REQUEST_TEMPLATE.md').is_file()
    assert not (ROOT / '.github' / 'pull_request_template.md').exists()


def test_release_notes_reject_an_empty_section_and_a_bad_version(tmp_path):
    with pytest.raises(subprocess.CalledProcessError):
        run_notes(
            tmp_path,
            '1.2.3',
            '## [1.2.3] - 2026-01-01\n\n## [1.2.2] - 2025-12-01\n\n- old\n',
        )
    with pytest.raises(subprocess.CalledProcessError):
        run_notes(tmp_path, '1.2', '## [1.2] - 2026-01-01\n\n- x\n')
