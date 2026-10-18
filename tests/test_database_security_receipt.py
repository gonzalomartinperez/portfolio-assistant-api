"""Full Java inventory and artifact binding are required for vendor receipts."""

import json

import pytest

from scripts.database_security_receipt import receipt

ID = 'sha256:' + 'a' * 64
REFERENCE = 'neo4j:5.26.32-community-trixie@sha256:' + 'b' * 64
EXPECTED = {
    'reference': REFERENCE,
    'platform': 'linux/amd64',
    'manifest_digest': 'sha256:' + 'd' * 64,
    'config_digest': ID,
}
SCANNER = {
    'Version': '0.75.0',
    'JavaDB': {'Version': 1, 'UpdatedAt': '2026-10-17T01:00:00Z'},
    'VulnerabilityDB': {'Version': 2, 'UpdatedAt': '2026-10-17T01:00:00Z'},
}


def report():
    return {
        'SchemaVersion': 2,
        'ArtifactType': 'container_image',
        'ArtifactName': REFERENCE,
        'Metadata': {'ImageID': ID, 'RepoDigests': ['neo4j@sha256:' + 'b' * 64]},
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
    result = receipt(json.dumps(report()), ID, REFERENCE, SCANNER, EXPECTED)
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
            receipt(json.dumps(value), identifier, REFERENCE, scanner, EXPECTED)


@pytest.mark.parametrize(
    ('header', 'java_severity', 'java_fixed', 'blocked', 'counts'),
    [
        pytest.param(True, None, '', True, (1, 0, 0), id='unfixed-header-critical'),
        pytest.param(
            False, 'CRITICAL', '', True, (1, 0, 0), id='unfixed-java-critical'
        ),
        pytest.param(
            False, 'CRITICAL', '2.22.3', True, (1, 0, 0), id='fixable-critical'
        ),
        pytest.param(True, 'HIGH', '2.22.3', True, (1, 1, 0), id='mixed-critical-high'),
        pytest.param(False, 'HIGH', '2.22.3', True, (0, 1, 0), id='fixable-high'),
        pytest.param(False, 'HIGH', '', False, (0, 0, 1), id='unfixed-high-visible'),
        pytest.param(False, None, '', False, (0, 0, 0), id='no-findings-not-approval'),
    ],
)
def test_cli_vendor_gate_preserves_complete_findings(
    tmp_path, monkeypatch, capsys, header, java_severity, java_fixed, blocked, counts
):
    from scripts.database_security_receipt import main

    monkeypatch.setattr(
        'scripts.database_security_receipt.verify_registry', lambda _: None
    )

    monkeypatch.setattr(
        'scripts.database_security_receipt.receipt',
        lambda raw, image_id, reference, scanner, expected: receipt(
            raw, image_id, reference, scanner, EXPECTED
        ),
    )

    value = report()
    if not header:
        value['Results'][0]['Vulnerabilities'] = []
    value['Results'][1]['Vulnerabilities'] = (
        [
            {
                'VulnerabilityID': 'CVE-synthetic-java',
                'PkgName': 'jackson-core',
                'InstalledVersion': '2.22.2',
                'Severity': java_severity,
                'FixedVersion': java_fixed,
            }
        ]
        if java_severity is not None
        else []
    )
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
    if blocked:
        with pytest.raises(SystemExit, match='findings'):
            main()
    else:
        main()
    output = json.loads(capsys.readouterr().out)
    assert output['counts']['critical'] == counts[0]
    assert output['counts']['fixable_high'] == counts[1]
    assert output['counts']['unresolved_high'] == counts[2]
    assert output['production_accepted'] is False


def test_other_artifact_or_relabelled_report_cannot_match_reviewed_descriptor():
    for mode in ('name', 'digests', 'config', 'reference'):
        value = report()
        identifier = ID
        reference = REFERENCE
        if mode == 'name':
            value['ArtifactName'] = 'other-image@sha256:' + 'b' * 64
        if mode == 'digests':
            value['Metadata']['RepoDigests'] = ['neo4j@sha256:' + 'c' * 64]
        if mode == 'config':
            identifier = 'sha256:' + 'c' * 64
            value['Metadata']['ImageID'] = identifier
        if mode == 'reference':
            reference = 'neo4j:5.26.32-community-trixie@sha256:' + 'c' * 64
        with pytest.raises(ValueError):
            receipt(json.dumps(value), identifier, reference, SCANNER, EXPECTED)


def test_committed_descriptor_matches_both_tested_service_references():
    from pathlib import Path

    import yaml

    expected = json.loads(Path('deploy/neo4j-image.json').read_text())
    compose = yaml.safe_load(Path('infra/compose/local.yaml').read_text())
    workflow = yaml.safe_load(Path('.github/workflows/quality.yml').read_text())
    assert compose['services']['neo4j']['image'] == expected['reference']
    for job in ('database', 'container'):
        assert (
            workflow['jobs'][job]['services']['neo4j']['image'] == expected['reference']
        )


def test_optional_database_dates_are_bounded_and_timezone_aware():
    from scripts.database_security_receipt import database_metadata

    for timestamp in ('x' * 1000, '2026-10-17T00:00:00', None, {}, 17):
        for key in ('UpdatedAt', 'NextUpdate', 'DownloadedAt'):
            if timestamp is None and key != 'UpdatedAt':
                continue
            with pytest.raises(ValueError):
                database_metadata(
                    {'Version': 1, 'UpdatedAt': '2026-10-17T01:00:00Z', key: timestamp}
                )


def test_registry_chain_checks_actual_content_and_amd64_configuration():
    import hashlib

    from scripts.database_security_receipt import verify_manifest_chain

    manifest = json.dumps({'config': {'digest': ID}}).encode()
    manifest_digest = 'sha256:' + hashlib.sha256(manifest).hexdigest()
    index = json.dumps(
        {
            'manifests': [
                {
                    'digest': manifest_digest,
                    'platform': {'architecture': 'amd64', 'os': 'linux'},
                }
            ]
        }
    ).encode()
    expected = {
        'reference': 'neo4j:5.26.32-community-trixie@sha256:'
        + hashlib.sha256(index).hexdigest(),
        'manifest_digest': manifest_digest,
        'config_digest': ID,
    }
    verify_manifest_chain(index, manifest, expected)
    for first, second, descriptor in [
        (index + b' ', manifest, expected),
        (index, manifest + b' ', expected),
        (index, manifest, {**expected, 'config_digest': 'sha256:' + 'c' * 64}),
    ]:
        with pytest.raises(ValueError):
            verify_manifest_chain(first, second, descriptor)


def test_large_unfixed_header_inventory_keeps_all_counts_without_unbounded_detail():
    value = report()
    value['Results'][0]['Vulnerabilities'] += [
        {
            'VulnerabilityID': f'CVE-synthetic-{index}',
            'PkgName': 'linux-libc-dev',
            'Severity': 'LOW',
            'FixedVersion': '',
        }
        for index in range(1000)
    ]
    result = receipt(json.dumps(value), ID, REFERENCE, SCANNER, EXPECTED)
    assert result['counts']['total'] == 1001
    assert result['counts']['critical'] == 1
    assert len(result['relevant_findings']) == 1


def test_vendor_assessment_is_explicit_and_cannot_be_softened():
    from pathlib import Path

    import yaml

    workflow = yaml.safe_load(Path('.github/workflows/quality.yml').read_text())
    triggers = workflow.get('on', workflow.get(True))
    option = triggers['workflow_dispatch']['inputs']['verify_vendor_image']
    assert option['type'] == 'boolean' and option['default'] is False
    steps = workflow['jobs']['container']['steps']
    deep = next(step for step in steps if 'Deep-scan' in step.get('name', ''))
    assert (
        deep['if']
        == "github.event_name == 'workflow_dispatch' && inputs.verify_vendor_image"
    )
    assert not deep.get('continue-on-error', False)
    assert '--ignorefile' in deep['run'] and '--list-all-pkgs' in deep['run']
    assert 'scripts.database_security_receipt' in deep['run']
    selected = json.loads(Path('deploy/neo4j-image.json').read_text())
    compose = yaml.safe_load(Path('infra/compose/local.yaml').read_text())
    assert selected['reference'] == compose['services']['neo4j']['image']


@pytest.mark.parametrize(
    'failure',
    [
        KeyError('synthetic-private'),
        IndexError('synthetic-private'),
        AttributeError('synthetic-private'),
    ],
)
def test_malformed_registry_descriptor_has_bounded_cli_diagnostics(
    monkeypatch, capsys, failure
):
    import sys

    import scripts.database_security_receipt as module

    def invalid(expected):
        raise failure

    monkeypatch.setattr(module, 'verify_registry', invalid)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'receipt',
            '--report',
            'unused',
            '--image-id-file',
            'unused',
            '--scanner-version',
            'unused',
            '--reference',
            REFERENCE,
        ],
    )
    with pytest.raises(SystemExit) as result:
        module.main()
    assert (
        str(result.value) == 'Missing, incomplete or mismatched vendor security receipt'
    )
    assert 'synthetic-private' not in capsys.readouterr().out
