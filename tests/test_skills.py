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
        'explicit-only-claude',
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
    elif mutation in ('permission-metadata', 'duplicate-key', 'explicit-only-claude'):
        value = (
            'allowed-tools: Bash(*)'
            if mutation == 'permission-metadata'
            else (
                'disable-model-invocation: true'
                if mutation == 'explicit-only-claude'
                else 'name: api-example'
            )
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


@pytest.mark.parametrize('setting', ['false', '"true"', 'null', '[]'])
def test_codex_policy_cannot_disable_automatic_selection(catalog, setting):
    client = catalog / '.claude/skills/api-example/agents/openai.yaml'
    client.parent.mkdir()
    client.write_text(f'policy:\n  allow_implicit_invocation: {setting}\n')
    assert any('automatic skill selection' in error for error in validate(catalog))


def test_codex_explicit_true_and_absent_policy_support_automatic_selection(catalog):
    client = catalog / '.claude/skills/api-example/agents/openai.yaml'
    client.parent.mkdir()
    for source in (
        'policy:\n  allow_implicit_invocation: true\n',
        'interface:\n  display_name: Example\n',
    ):
        client.write_text(source)
        assert validate(catalog) == []


@pytest.mark.parametrize(
    'source', ['[]', 'null', 'policy: []', 'policy: [private-sentinel']
)
def test_invalid_client_metadata_is_rejected_without_echoing_values(catalog, source):
    client = catalog / '.claude/skills/api-example/agents/openai.yaml'
    client.parent.mkdir()
    client.write_text(source)
    errors = validate(catalog)
    assert any('automatic skill selection' in error for error in errors)
    assert 'private-sentinel' not in str(errors)
