"""Structural checks for the judge calibration scaffolding (PAA-D5, M2-15).

jsonschema is not in uv.lock, so validation is a small stdlib check of the
schema subset the label schema uses (type, enum, pattern, length, required,
additionalProperties).
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CAL = ROOT / 'evals' / 'calibration'
SCHEMA = json.loads((CAL / 'label.schema.json').read_text())

VALID = {
    'id': 'lbl-001',
    'criterion': 'helpful_complete',
    'item_id': 'gold-en-001',
    'locale': 'en',
    'question': 'Which languages are used?',
    'answer_ref': 'private://run-2026-11/abc123',
    'label': 'pass',
    'labeller': 'agent-a',
    'labeller_kind': 'agent',
    'rationale': 'Answers directly.',
    'split': 'dev',
    'created': '2026-11-14',
    'spot_checked': False,
    'spot_check_label': None,
}


def errors(doc: dict) -> list[str]:
    out = [f'missing {k}' for k in SCHEMA['required'] if k not in doc]
    for key, value in doc.items():
        spec = SCHEMA['properties'].get(key)
        if spec is None:
            out.append(f'unknown {key}')
            continue
        if 'enum' in spec and value not in spec['enum']:
            out.append(f'enum {key}')
        if spec.get('type') == 'string':
            if not isinstance(value, str):
                out.append(f'type {key}')
                continue
            if len(value) < spec.get('minLength', 0) or len(value) > spec.get(
                'maxLength', 10**9
            ):
                out.append(f'length {key}')
            if 'pattern' in spec and not re.search(spec['pattern'], value):
                out.append(f'pattern {key}')
        if spec.get('type') == 'boolean' and not isinstance(value, bool):
            out.append(f'type {key}')
    return out


def test_schema_is_structurally_valid_2020_12() -> None:
    assert SCHEMA['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
    assert SCHEMA['type'] == 'object'
    assert SCHEMA['additionalProperties'] is False
    assert set(SCHEMA['required']) == set(SCHEMA['properties'])
    assert SCHEMA['properties']['criterion']['enum'] == ['helpful_complete', 'tone_fit']
    for spec in SCHEMA['properties'].values():
        assert 'type' in spec or 'enum' in spec


def test_valid_label_passes() -> None:
    assert errors(VALID) == []
    assert errors({**VALID, 'spot_checked': True, 'spot_check_label': 'fail'}) == []


@pytest.mark.parametrize(
    ('patch', 'expected'),
    [
        ({'answer': 'raw answer text'}, 'unknown answer'),
        ({'criterion': 'safety'}, 'enum criterion'),
        ({'answer_ref': 'The answer text itself'}, 'pattern answer_ref'),
        ({'label': 'maybe'}, 'enum label'),
    ],
)
def test_invalid_labels_rejected(patch: dict, expected: str) -> None:
    assert expected in errors({**VALID, **patch})


def test_html_has_no_remote_resources() -> None:
    html = (CAL / 'review.html').read_text()
    assert not re.search(r'https?://', html)
    assert not re.search(r'<script[^>]*\ssrc=', html, re.IGNORECASE)
    assert not re.search(r'<link[^>]*\shref=', html, re.IGNORECASE)
    assert 'fetch(' not in html and 'XMLHttpRequest' not in html


def test_rubrics_have_front_matter() -> None:
    for name in ('helpful_complete', 'tone_fit'):
        text = (ROOT / 'evals' / 'judge' / f'{name}.md').read_text()
        head = text.split('---')[1]
        for key in ('id:', 'version:', 'owner:', 'last-reviewed:'):
            assert key in head


def test_no_ci_workflow_references_judge() -> None:
    for wf in (ROOT / '.github' / 'workflows').rglob('*'):
        if wf.is_file():
            assert 'judge' not in wf.read_text().lower(), wf
