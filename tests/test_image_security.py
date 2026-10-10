"""Security gates fail closed on incomplete reports and incorrect artifacts."""

import json

import pytest

from scripts.image_security import evaluate

IMAGE_ID = 'sha256:' + 'a' * 64


def report(severity='LOW', fixed=''):
    return {
        'SchemaVersion': 2,
        'ArtifactType': 'container_image',
        'Metadata': {'ImageID': IMAGE_ID},
        'Results': [
            {
                'Class': 'os-pkgs',
                'Vulnerabilities': [
                    {
                        'VulnerabilityID': 'CVE-example',
                        'Severity': severity,
                        'FixedVersion': fixed,
                    }
                ],
            }
        ],
    }


@pytest.mark.parametrize(
    ('severity', 'fixed', 'critical', 'fixable', 'unresolved'),
    [
        ('LOW', '', 0, 0, 0),
        ('CRITICAL', '', 1, 0, 0),
        ('CRITICAL', '2.0', 1, 0, 0),
        ('HIGH', '2.0', 0, 1, 0),
        ('HIGH', '', 0, 0, 1),
        ('HIGH', '   ', 0, 0, 1),
    ],
)
def test_all_findings_remain_visible(severity, fixed, critical, fixable, unresolved):
    assert evaluate(json.dumps(report(severity, fixed)), IMAGE_ID) == {
        'critical': critical,
        'fixable_high': fixable,
        'unresolved_high': unresolved,
        'total': 1,
    }


@pytest.mark.parametrize('invalid', ['', '{}', '{', '[]'])
def test_missing_or_malformed_report_fails(invalid):
    with pytest.raises(ValueError):
        evaluate(invalid, IMAGE_ID)


def test_stale_image_report_fails():
    with pytest.raises(ValueError, match='tested image'):
        evaluate(json.dumps(report()), 'sha256:' + 'b' * 64)


def test_absent_os_inventory_fails():
    raw = report()
    raw['Results'][0]['Class'] = 'lang-pkgs'
    with pytest.raises(ValueError, match='operating system'):
        evaluate(json.dumps(raw), IMAGE_ID)


def test_language_findings_are_not_ignored():
    raw = report()
    extra = report('CRITICAL')['Results'][0]
    extra['Class'] = 'lang-pkgs'
    raw['Results'].append(extra)
    assert evaluate(json.dumps(raw), IMAGE_ID)['critical'] == 1


@pytest.mark.parametrize(('severity', 'fixed'), [('CRITICAL', ''), ('HIGH', '2.0')])
def test_cli_rejects_blocking_findings(tmp_path, monkeypatch, severity, fixed):
    from scripts.image_security import main

    path = tmp_path / 'report.json'
    path.write_text(json.dumps(report(severity, fixed)))
    monkeypatch.setattr(
        'sys.argv', ['image-security', '--report', str(path), '--image-id', IMAGE_ID]
    )
    with pytest.raises(SystemExit, match='critical or fixable high'):
        main()
