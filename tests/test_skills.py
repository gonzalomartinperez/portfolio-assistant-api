"""Catalog checks must catch broken discovery and unsafe/ambiguous resources."""

from pathlib import Path

import pytest

from scripts.validate_skills import validate


@pytest.fixture
def catalog(tmp_path):
    (tmp_path / 'AGENTS.md').write_text('Canonical operating contract.\n')
    (tmp_path / 'CLAUDE.md').write_text('@AGENTS.md\n')
    canonical = tmp_path / '.claude/skills/api-example'
    canonical.mkdir(parents=True)
    (canonical / 'SKILL.md').write_text(
        '---\nname: api-example\ndescription: "Exercise a fixture workflow."\n---\n\nRead [contract](../../../AGENTS.md).\n'
    )
    discovery = tmp_path / '.agents/skills'
    discovery.mkdir(parents=True)
    (discovery / 'api-example').symlink_to('../../.claude/skills/api-example')
    return tmp_path


def test_real_catalog_is_portable():
    assert validate(Path(__file__).resolve().parents[1]) == []


def test_relative_discovery_works_after_checkout_relocation(catalog, tmp_path_factory):
    import shutil

    relocated = tmp_path_factory.mktemp('relocated') / 'repo'
    shutil.copytree(catalog, relocated, symlinks=True)
    assert validate(relocated) == []


@pytest.mark.parametrize(
    'mutation',
    [
        'broken-link',
        'outside-link',
        'duplicate-name',
        'permission-metadata',
        'duplicate-key',
        'private-path',
        'scaffold',
        'missing-reference',
        'secret',
        'missing-command',
    ],
)
def test_catalog_rejects_invalid_or_unsafe_resources(catalog, mutation):
    skill = catalog / '.claude/skills/api-example/SKILL.md'
    entry = catalog / '.agents/skills/api-example'
    if mutation in ('broken-link', 'outside-link'):
        entry.unlink()
        entry.symlink_to('missing' if mutation == 'broken-link' else '/tmp')
    elif mutation == 'duplicate-name':
        other = catalog / '.claude/skills/api-other'
        other.mkdir()
        (other / 'SKILL.md').write_text(skill.read_text())
    elif mutation in ('permission-metadata', 'duplicate-key'):
        value = (
            'allowed-tools: Bash(*)'
            if mutation == 'permission-metadata'
            else 'name: api-example'
        )
        skill.write_text(
            skill.read_text().replace('description:', value + '\ndescription:')
        )
    else:
        suffix = {
            'private-path': '/home/' + 'example/private/file',
            'scaffold': 'TODO: fill this in',
            'missing-reference': '[missing](references/absent.md)',
            'secret': 'sk-' + 'x' * 40,
            'missing-command': 'uv run python -m scripts.absent',
        }[mutation]
        skill.write_text(skill.read_text() + '\n' + suffix)
    errors = validate(catalog)
    assert errors
    assert 'x' * 40 not in str(errors)
