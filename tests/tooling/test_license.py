"""Licensing consistency fails closed without changing third-party terms."""

from pathlib import Path

import pytest

from scripts.check_license import license_findings


@pytest.fixture
def licensed_fixture(tmp_path):
    (tmp_path / 'LICENSE').write_bytes(Path('LICENSE').read_bytes())
    (tmp_path / 'pyproject.toml').write_text(
        '[project]\nname="fixture-api"\nversion="0.1.0"\nlicense="MIT"\n'
        'license-files=["LICENSE","THIRD_PARTY_NOTICES.md"]\n'
    )
    (tmp_path / 'uv.lock').write_text(
        '[[package]]\nname="fixture-api"\nversion="0.1.0"\nsource={virtual="."}\n'
    )
    (tmp_path / 'README.md').write_text(
        '## Software license\n\n[MIT](LICENSE) · [Notices](THIRD_PARTY_NOTICES.md)\n'
    )
    (tmp_path / 'THIRD_PARTY_NOTICES.md').write_text(
        '## Scope\n\n[MIT](LICENSE) covers software; content retains its terms.\n'
    )
    return tmp_path


def test_actual_repository_and_complete_fixture_are_consistent(licensed_fixture):
    assert license_findings(Path('.')) == []
    assert license_findings(licensed_fixture) == []


@pytest.mark.parametrize(
    'mutation',
    [
        'restriction',
        'preface-restriction',
        'year-placeholder',
        'holder-placeholder',
        'manifest',
        'lock',
        'missing-license',
        'missing-notices',
        'readme-link',
        'scope',
    ],
)
def test_invalid_licensing_is_rejected(licensed_fixture, mutation):
    root = licensed_fixture
    if mutation == 'preface-restriction':
        source = (root / 'LICENSE').read_text()
        (root / 'LICENSE').write_text(
            source.replace(
                'Permission is hereby granted,',
                'No commercial use.\n\nPermission is hereby granted,',
            )
        )
    elif mutation == 'restriction':
        with (root / 'LICENSE').open('a') as source:
            source.write('\nNo commercial use.\n')
    elif mutation in ('year-placeholder', 'holder-placeholder'):
        import re

        source = (root / 'LICENSE').read_text()
        placeholder = (
            'Copyright (c) <YEAR> Owner'
            if mutation == 'year-placeholder'
            else 'Copyright (c) 2026 <COPYRIGHT HOLDER>'
        )
        (root / 'LICENSE').write_text(
            re.sub(r'Copyright \(c\) [^\n]+', placeholder, source)
        )
    elif mutation == 'manifest':
        path = root / 'pyproject.toml'
        path.write_text(path.read_text().replace('license="MIT"', 'license="ISC"'))
    elif mutation == 'lock':
        path = root / 'uv.lock'
        path.write_text(path.read_text().replace('version="0.1.0"', 'version="0.2.0"'))
    elif mutation in ('missing-license', 'missing-notices'):
        (
            root
            / ('LICENSE' if mutation == 'missing-license' else 'THIRD_PARTY_NOTICES.md')
        ).unlink()
    elif mutation == 'readme-link':
        (root / 'README.md').write_text('## Software license\n')
    else:
        (root / 'THIRD_PARTY_NOTICES.md').write_text('[MIT](LICENSE)\n')
    assert license_findings(root)
