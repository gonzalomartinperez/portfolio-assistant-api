"""Gate the complete scanner report without hiding unresolved OS findings."""

import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class Vulnerability(BaseModel):
    vulnerability_id: str = Field(alias='VulnerabilityID', min_length=1)
    severity: Literal['UNKNOWN', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] = Field(
        alias='Severity'
    )
    fixed_version: str = Field(default='', alias='FixedVersion')


class Result(BaseModel):
    category: str = Field(alias='Class')
    vulnerabilities: list[Vulnerability] = Field(
        default_factory=list, alias='Vulnerabilities'
    )


class Metadata(BaseModel):
    image_id: str = Field(alias='ImageID', pattern=r'^sha256:[0-9a-f]{64}$')


class Report(BaseModel):
    schema_version: Literal[2] = Field(alias='SchemaVersion')
    artifact_type: Literal['container_image'] = Field(alias='ArtifactType')
    metadata: Metadata = Field(alias='Metadata')
    results: list[Result] = Field(alias='Results', min_length=1)


def evaluate(raw: str, image_id: str) -> dict[str, int]:
    report = Report.model_validate_json(raw, strict=True)
    if report.metadata.image_id != image_id:
        raise ValueError('Scanner report does not match the tested image')
    if not any(result.category == 'os-pkgs' for result in report.results):
        raise ValueError('Scanner report omits the operating system')
    findings = [item for result in report.results for item in result.vulnerabilities]
    return {
        'critical': sum(item.severity == 'CRITICAL' for item in findings),
        'fixable_critical': sum(
            item.severity == 'CRITICAL' and bool(item.fixed_version.strip())
            for item in findings
        ),
        'fixable_high': sum(
            item.severity == 'HIGH' and bool(item.fixed_version.strip())
            for item in findings
        ),
        'unresolved_high': sum(
            item.severity == 'HIGH' and not item.fixed_version.strip()
            for item in findings
        ),
        'total': len(findings),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--image-id', required=True)
    args = parser.parse_args()
    try:
        summary = evaluate(args.report.read_text(), args.image_id)
    except OSError, ValueError, ValidationError:
        raise SystemExit(
            'Image security report is missing, invalid or mismatched'
        ) from None
    print(json.dumps(summary, sort_keys=True))
    if summary['critical'] or summary['fixable_high']:
        raise SystemExit('Image contains critical or fixable high vulnerabilities')


if __name__ == '__main__':
    main()
