"""Full Java inventory and artifact binding are required for vendor receipts."""

import json

import pytest

from scripts.database_security_receipt import receipt

ID = 'sha256:' + 'a' * 64
REFERENCE = 'neo4j:5.26.32-community-trixie@sha256:' + 'b' * 64
SCANNER = {
    'Version': '0.75.0',
    'JavaDB': {'Version': 1, 'UpdatedAt': '2026-10-17T01:00:00Z'},
    'VulnerabilityDB': {'Version': 2, 'UpdatedAt': '2026-10-17T01:00:00Z'},
}


def report():
    return {
        'SchemaVersion': 2,
        'ArtifactType': 'container_image',
        'Metadata': {'ImageID': ID},
        'CreatedAt': '2026-10-17T00:00:00Z',
        'Results': [
            {
                'Class': 'os-pkgs',
                'Vulnerabilities': [
                    {
                        'VulnerabilityID': 'CVE-synthetic-header',
                        'PkgName': 'linux-libc-dev',
                        'Severity': 'CRITICAL',
                        'FixedVersion': '',
                    }
                ],
            },
            {
                'Class': 'lang-pkgs',
                'Type': 'jar',
                'Packages': [
                    {
                        'Name': 'com.fasterxml.jackson.core:jackson-core',
                        'Version': '2.22.3',
                    }
                ],
                'Vulnerabilities': [],
            },
        ],
    }


def test_unfixed_header_remains_visible_and_is_not_production_acceptance():
    result = receipt(json.dumps(report()), ID, REFERENCE, SCANNER)
    assert result['production_accepted'] is False
    assert result['counts']['critical'] == 1
    assert result['counts']['fixable_critical'] == 0
    assert result['jackson_packages'][0]['Version'] == '2.22.3'
    assert result['relevant_findings'][0]['PkgName'] == 'linux-libc-dev'


def test_missing_java_os_scanner_or_wrong_image_cannot_produce_release_receipt():
    for mode in ('java', 'packages', 'os', 'image', 'scanner'):
        value = report()
        scanner = SCANNER
        identifier = ID
        if mode == 'java':
            value['Results'] = value['Results'][:1]
        if mode == 'packages':
            value['Results'][1]['Packages'] = []
        if mode == 'os':
            value['Results'] = value['Results'][1:]
        if mode == 'image':
            identifier = 'sha256:' + 'c' * 64
        if mode == 'scanner':
            scanner = {}
        with pytest.raises(ValueError):
            receipt(json.dumps(value), identifier, REFERENCE, scanner)


def test_cli_refuses_fixable_java_findings_without_suppressing_them(
    tmp_path, monkeypatch, capsys
):
    from scripts.database_security_receipt import main

    value = report()
    value['Results'][1]['Vulnerabilities'] = [
        {
            'VulnerabilityID': 'CVE-synthetic-java',
            'PkgName': 'jackson-core',
            'InstalledVersion': '2.22.2',
            'Severity': 'HIGH',
            'FixedVersion': '2.22.3',
        }
    ]
    paths = [tmp_path / name for name in ('report.json', 'id.txt', 'scanner.json')]
    paths[0].write_text(json.dumps(value))
    paths[1].write_text(ID)
    paths[2].write_text(json.dumps(SCANNER))
    monkeypatch.setattr(
        'sys.argv',
        [
            'receipt',
            '--report',
            str(paths[0]),
            '--image-id-file',
            str(paths[1]),
            '--scanner-version',
            str(paths[2]),
            '--reference',
            REFERENCE,
        ],
    )
    with pytest.raises(SystemExit, match='fixable critical/high'):
        main()
    output = json.loads(capsys.readouterr().out)
    assert output['counts']['critical'] == 1
    assert output['counts']['fixable_high'] == 1
    assert output['production_accepted'] is False
