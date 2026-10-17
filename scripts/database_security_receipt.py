"""Emit a bounded package-only release receipt; never a clean-stack claim."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from scripts.image_security import evaluate


def database_metadata(value: object) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('Version'), int):
        raise TypeError('missing database provenance')
    updated = value.get('UpdatedAt')
    if (
        not isinstance(updated, str)
        or len(updated) > 64
        or datetime.fromisoformat(updated).tzinfo is None
    ):
        raise ValueError('missing database timestamp')
    return {
        key: value[key]
        for key in ('Version', 'UpdatedAt', 'NextUpdate', 'DownloadedAt')
        if key in value
    }


def receipt(raw: str, image_id: str, reference: str, scanner: dict) -> dict:
    summary = evaluate(raw, image_id)
    report = json.loads(raw)
    if (
        scanner.get('Version') != '0.75.0'
        or not scanner.get('JavaDB')
        or not scanner.get('VulnerabilityDB')
    ):
        raise ValueError('missing scanner provenance')
    java = [
        result
        for result in report['Results']
        if result.get('Class') == 'lang-pkgs' and result.get('Type') == 'jar'
    ]
    if not java:
        raise ValueError('Java inventory is required')
    packages = [
        {key: package.get(key) for key in ('Name', 'Version')}
        for result in java
        for package in result.get('Packages', [])
        if 'jackson' in package.get('Name', '').lower()
    ]
    if not packages or len(packages) > 100:
        raise ValueError('bounded Jackson package inventory required')
    relevant = []
    for result in report['Results']:
        for item in result.get('Vulnerabilities', []):
            if (
                item.get('PkgName') == 'linux-libc-dev'
                or 'jackson' in item.get('PkgName', '').lower()
            ):
                relevant.append(
                    {
                        key: item.get(key)
                        for key in (
                            'VulnerabilityID',
                            'PkgName',
                            'InstalledVersion',
                            'FixedVersion',
                            'Severity',
                        )
                    }
                )
    if len(relevant) > 100:
        raise ValueError('unbounded relevant findings')
    return {
        'reference': reference,
        'image_id': image_id,
        'created_at': report.get('CreatedAt'),
        'scanner': {
            'Version': scanner['Version'],
            'VulnerabilityDB': database_metadata(scanner['VulnerabilityDB']),
            'JavaDB': database_metadata(scanner['JavaDB']),
        },
        'jackson_packages': packages,
        'counts': summary,
        'relevant_findings': relevant,
        'production_accepted': False,
        'scope': 'Full OS and Java inventory; header findings do not identify the running host kernel.',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--image-id-file', type=Path, required=True)
    parser.add_argument('--scanner-version', type=Path, required=True)
    parser.add_argument('--reference', required=True)
    args = parser.parse_args()
    try:
        result = receipt(
            args.report.read_text(),
            args.image_id_file.read_text().strip(),
            args.reference,
            json.loads(args.scanner_version.read_text()),
        )
    except OSError, ValueError, TypeError:
        raise SystemExit(
            'Missing, incomplete or mismatched vendor security receipt'
        ) from None
    print(json.dumps(result, sort_keys=True))
    # Same remediation gate as PostgreSQL; unresolved critical findings remain release blockers.
    if result['counts']['fixable_critical'] or result['counts']['fixable_high']:
        raise SystemExit('Vendor image retains fixable critical/high findings')


if __name__ == '__main__':
    main()
