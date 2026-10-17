"""Emit a bounded package-only release receipt; never a clean-stack claim."""

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

from scripts.image_security import evaluate


def database_metadata(value: object) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('Version'), int):
        raise TypeError('missing database provenance')
    for key in ('UpdatedAt', 'NextUpdate', 'DownloadedAt'):
        stamp = value.get(key)
        if stamp is None and key != 'UpdatedAt':
            continue
        if (
            not isinstance(stamp, str)
            or len(stamp) > 64
            or datetime.fromisoformat(stamp).tzinfo is None
        ):
            raise ValueError('invalid database timestamp')
    return {
        key: value[key]
        for key in ('Version', 'UpdatedAt', 'NextUpdate', 'DownloadedAt')
        if key in value
    }


def verify_manifest_chain(
    index_raw: bytes, manifest_raw: bytes, expected: dict
) -> None:
    index_digest = expected['reference'].split('@')[1]
    if (
        'sha256:' + hashlib.sha256(index_raw).hexdigest() != index_digest
        or 'sha256:' + hashlib.sha256(manifest_raw).hexdigest()
        != expected['manifest_digest']
    ):
        raise ValueError('vendor manifest checksum mismatch')
    index = json.loads(index_raw)
    if not any(
        item.get('digest') == expected['manifest_digest']
        and item.get('platform') == {'architecture': 'amd64', 'os': 'linux'}
        for item in index.get('manifests', [])
    ):
        raise ValueError('vendor platform chain mismatch')
    if (
        json.loads(manifest_raw).get('config', {}).get('digest')
        != expected['config_digest']
    ):
        raise ValueError('vendor config chain mismatch')


def verify_registry(expected: dict) -> None:
    # Only official public Neo4j metadata; anonymous pull token never leaves this scope.
    with urllib.request.urlopen(
        'https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/neo4j:pull',
        timeout=15,
    ) as response:
        raw = response.read(32769)
    if len(raw) > 32768:
        raise ValueError('registry token metadata limit')
    token = json.loads(raw)['token']
    headers = {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json',
    }

    def manifest(digest: str) -> bytes:
        if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
            raise ValueError('invalid registry digest')
        request = urllib.request.Request(
            'https://registry-1.docker.io/v2/library/neo4j/manifests/' + digest,
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read(131073)
        if len(body) > 131072:
            raise ValueError('registry manifest limit')
        return body

    verify_manifest_chain(
        manifest(expected['reference'].split('@')[1]),
        manifest(expected['manifest_digest']),
        expected,
    )


def receipt(
    raw: str, image_id: str, reference: str, scanner: dict, expected: dict | None = None
) -> dict:
    summary = evaluate(raw, image_id)
    report = json.loads(raw)
    expected = (
        expected
        if expected is not None
        else json.loads(
            (Path(__file__).parents[1] / 'deploy/neo4j-image.json').read_text()
        )
    )
    if (
        set(expected) != {'reference', 'platform', 'manifest_digest', 'config_digest'}
        or expected['platform'] != 'linux/amd64'
    ):
        raise ValueError('invalid vendor descriptor')
    if (
        not re.fullmatch(
            r'neo4j:5\.26\.\d+-community-trixie@sha256:[a-f0-9]{64}', reference
        )
        or reference != expected['reference']
    ):
        raise ValueError('unexpected vendor reference')
    if any(
        not isinstance(expected[key], str)
        or not re.fullmatch(r'sha256:[a-f0-9]{64}', expected[key])
        for key in ('manifest_digest', 'config_digest')
    ):
        raise ValueError('invalid vendor digest')
    if image_id != expected['config_digest'] or report.get('ArtifactName') != reference:
        raise ValueError('vendor image provenance mismatch')
    index = reference.split('@')[1]
    approved = {
        f'{repository}@{digest}'
        for repository in ('neo4j', 'library/neo4j', 'docker.io/library/neo4j')
        for digest in (index, expected['manifest_digest'])
    }
    repo_digests = report['Metadata'].get('RepoDigests')
    if not isinstance(repo_digests, list) or not any(
        item in approved for item in repo_digests if isinstance(item, str)
    ):
        raise ValueError('vendor manifest chain mismatch')

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
            relevant_package = (
                item.get('PkgName') == 'linux-libc-dev'
                or 'jackson' in item.get('PkgName', '').lower()
            )
            actionable = item.get('Severity') == 'CRITICAL' or (
                item.get('Severity') == 'HIGH'
                and bool(item.get('FixedVersion', '').strip())
            )
            if relevant_package and actionable:
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
        'source_descriptor': expected,
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
        'relevant_selection': 'Critical or fixable high findings in linux-libc-dev/Jackson; complete severity totals include every package and finding.',
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
        expected = json.loads(
            (Path(__file__).parents[1] / 'deploy/neo4j-image.json').read_text()
        )
        verify_registry(expected)
        result = receipt(
            args.report.read_text(),
            args.image_id_file.read_text().strip(),
            args.reference,
            json.loads(args.scanner_version.read_text()),
            expected,
        )
    except OSError, ValueError, TypeError, KeyError, IndexError, AttributeError:
        raise SystemExit(
            'Missing, incomplete or mismatched vendor security receipt'
        ) from None
    print(json.dumps(result, sort_keys=True))
    # Same remediation gate as PostgreSQL; unresolved critical findings remain release blockers.
    if result['counts']['fixable_critical'] or result['counts']['fixable_high']:
        raise SystemExit('Vendor image retains fixable critical/high findings')


if __name__ == '__main__':
    main()
