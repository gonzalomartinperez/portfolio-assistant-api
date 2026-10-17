"""Check repository licensing consistency, not third-party legal compliance."""

import hashlib
import re
import tomllib
from pathlib import Path

# Standard MIT permission/warranty text normalized for wrapping; copyright is separate.
MIT_GRANT_SHA256 = 'fe2a9817987f862eaced948f0468c7f51d2fedfc48c5c505b246a49a3870e9a5'


def license_findings(root: Path) -> list[str]:
    findings = []
    try:
        source = (root / 'LICENSE').read_text()
        start = source.find('Permission is hereby granted, free of charge,')
        header = [line.strip() for line in source[:start].splitlines() if line.strip()]
        grant = re.sub(r'\s+', ' ', source[start:]).strip()
        if (
            not header
            or header[0] != 'MIT License'
            or len(header) < 2
            or any(
                not re.fullmatch(r'Copyright \(c\) \d{4}(?:-\d{4})? \S.+', line)
                for line in header[1:]
            )
            or re.search(r'<[^>]+>', source[:start])
            or start < 0
            or hashlib.sha256(grant.encode()).hexdigest() != MIT_GRANT_SHA256
        ):
            findings.append(
                'LICENSE must retain the standard MIT grant and copyright notice.'
            )
        project = tomllib.loads((root / 'pyproject.toml').read_text())['project']
        if project.get('license') != 'MIT' or not {
            'LICENSE',
            'THIRD_PARTY_NOTICES.md',
        } <= set(project.get('license-files', [])):
            findings.append(
                'Project SPDX/license-file metadata must identify MIT and its notices.'
            )
        # uv's virtual root records name/version, not SPDX; do not invent lock fields.
        packages = tomllib.loads((root / 'uv.lock').read_text()).get('package', [])
        owned = [
            package
            for package in packages
            if isinstance(package, dict) and package.get('name') == project.get('name')
        ]
        if len(owned) != 1 or owned[0].get('version') != project.get('version'):
            findings.append('The lock root must match project identity/version.')
        readme = (root / 'README.md').read_text()
        if (
            not re.search(r'^## Software license$', readme, re.MULTILINE)
            or '](LICENSE)' not in readme
            or '](THIRD_PARTY_NOTICES.md)' not in readme
        ):
            findings.append(
                'README must link the software license and separate notices.'
            )
        notices = (root / 'THIRD_PARTY_NOTICES.md').read_text()
        if (
            not re.search(r'^## Scope$', notices, re.MULTILINE)
            or '](LICENSE)' not in notices
        ):
            findings.append('Separate notices must document scope and link LICENSE.')
    except OSError, ValueError, KeyError, TypeError:
        findings.append(
            'Required licensing files or metadata are missing or unreadable.'
        )
    return findings


def main() -> None:
    findings = license_findings(Path(__file__).resolve().parents[1])
    for finding in findings:
        print(finding)
    print(f'License consistency: {len(findings)} findings. Not a legal audit.')
    raise SystemExit(bool(findings))


if __name__ == '__main__':
    main()
