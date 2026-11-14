"""Collectors: read whatever artifacts exist; an absent input is `missing`, never a pass."""

import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

# Criteria with no collector yet stay unmet (scorecard.md section 5); never inferred.
PENDING = {
    'D1': ['guard_violations', 'negative_fixtures_pass', 'import_linter'],
    'D2': ['max_cc', 'dead_code'],
    'D3': ['diff_coverage', 'mutation_score', 'flaky_30d'],
    'D4': ['pr_p50', 'pr_p95', 'single_dependabot_pr', 'build_once_digest'],
    'D5': ['pinned_actions', 'zizmor_high', 'codeql_open_high', 'sbom_attested'],
    'D6': ['ttfe_p95_stubbed', 'error_rate', 'rss_growth', 'answer_cost_p95'],
    'D7': ['log_redaction_test', 'request_id_propagation_test', 'health_contract'],
    'D8': ['readme_headings', 'links_ok', 'adr_index', 'changelog_current'],
    'P1': ['problem_schema_valid'],
    'P2': ['ttft_budget'],
    'P4': ['oasdiff_clean', 'schemathesis'],
    'P5': ['consumer_compile'],
    'P6': ['standards_drift'],
}
BRANCH_FLOOR = 0.85  # rubrics D3 / scorecard.md: 85% branch coverage floor
AXES = (
    'D1',
    'D2',
    'D3',
    'D4',
    'D5',
    'D6',
    'D7',
    'D8',
    'P1',
    'P2',
    'P3',
    'P4',
    'P5',
    'P6',
)


def metric(value: float | None, source: str) -> dict:
    if value is None:
        return {'value': None, 'status': 'missing', 'source': source}
    return {'value': value, 'status': 'ok', 'source': source}


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except OSError, ValueError:
        return None


def ruff_findings(path: Path) -> float | None:
    data = read_json(path)
    return len(data) if isinstance(data, list) else None


def mypy_errors(path: Path) -> float | None:
    try:
        text = path.read_text()
    except OSError:
        return None
    if match := re.search(r'^Found (\d+) errors? in', text, re.MULTILINE):
        return int(match[1])
    return 0 if re.search(r'^Success: no issues found', text, re.MULTILINE) else None


def junit_totals(path: Path) -> dict[str, int] | None:
    try:
        root = ET.parse(path).getroot()
    except OSError, ET.ParseError:
        return None
    if root.tag not in ('testsuites', 'testsuite'):
        return None
    suites = [root] if root.tag == 'testsuite' else list(root)
    totals = {'total': 0, 'failures': 0, 'skipped': 0}
    try:
        for suite in suites:
            totals['total'] += int(suite.get('tests', 0))
            totals['failures'] += int(suite.get('failures', 0)) + int(
                suite.get('errors', 0)
            )
            totals['skipped'] += int(suite.get('skipped', 0))
    except ValueError, TypeError:
        return None
    return totals


def coverage_rates(path: Path) -> dict[str, float] | None:
    try:
        root = ET.parse(path).getroot()
        return {
            'line': float(root.attrib['line-rate']),
            'branch': float(root.attrib['branch-rate']),
        }
    except OSError, ET.ParseError, KeyError, ValueError:
        return None


def judged_scores(root: Path) -> tuple[str | None, dict[str, int]]:
    files = sorted((root / 'docs/evidence/scores').glob('*.md'))
    if not files:
        return None, {}
    latest = files[-1]
    scores = {}
    for line in latest.read_text().splitlines():
        if match := re.match(r'\|\s*(D[1-8]|P[1-6])\b[^|]*\|\s*\**(\d+)', line):
            scores[match[1]] = int(match[2])
    return latest.name, scores


def collect(artifacts: Path, root: Path = Path('.')) -> dict:
    m: dict[str, dict] = {}
    m['static.ruff_findings'] = metric(
        ruff_findings(artifacts / 'ruff.json'), 'artifacts/ruff.json'
    )
    m['static.mypy_errors'] = metric(
        mypy_errors(artifacts / 'mypy.txt'), 'artifacts/mypy.txt'
    )
    lanes = {}
    for lane in ('unit', 'integration'):
        totals = junit_totals(artifacts / f'{lane}.xml')
        lanes[lane] = totals
        for field in ('total', 'failures', 'skipped'):
            m[f'tests.{lane}.{field}'] = metric(
                totals[field] if totals else None, f'artifacts/{lane}.xml'
            )
    both = lanes['unit'] and lanes['integration']
    share = None
    if both:
        all_tests = lanes['unit']['total'] + lanes['integration']['total']
        share = lanes['integration']['total'] / all_tests if all_tests else None
    m['tests.integration_share'] = metric(share, 'unit.xml and integration.xml')
    cov = coverage_rates(artifacts / 'coverage.xml')
    m['coverage.line_rate'] = metric(cov['line'] if cov else None, 'coverage.xml')
    m['coverage.branch_rate'] = metric(cov['branch'] if cov else None, 'coverage.xml')
    mutation = read_json(artifacts / 'mutation.json')
    score = mutation.get('score') if isinstance(mutation, dict) else None
    m['mutation.score'] = metric(score, 'artifacts/mutation.json (placeholder)')
    sizes = read_json(artifacts / 'image-sizes.json')
    sizes = sizes if isinstance(sizes, dict) else {}
    for name in ('api', 'worker'):
        m[f'image.{name}_bytes'] = metric(
            sizes.get(f'{name}_bytes'), 'artifacts/image-sizes.json'
        )
    golden = read_json(artifacts / 'golden.json')
    rate = None
    if isinstance(golden, dict) and golden.get('total'):
        rate = golden.get('passed', 0) / golden['total']
    m['eval.golden_pass_rate'] = metric(rate, 'artifacts/golden.json')
    source, scores = judged_scores(root)
    for axis in AXES:
        m[f'judged.{axis}'] = metric(
            scores.get(axis),
            f'docs/evidence/scores/{source}' if source else 'not yet scored',
        )

    def val(key: str):
        return m[key]['value']

    def criterion(axis, name, value, ok, rule):
        status = 'unmet' if value is None else ('pass' if ok(value) else 'fail')
        return f'{axis}.{name}', {
            'axis': axis,
            'status': status,
            'value': value,
            'rule': rule,
        }

    unit_failures = val('tests.unit.failures')
    image = image_within_cap(root, m)
    criteria = dict(
        [
            criterion(
                'D2', 'mypy_errors', val('static.mypy_errors'), lambda v: v == 0, '== 0'
            ),
            criterion(
                'D2',
                'ruff_findings',
                val('static.ruff_findings'),
                lambda v: v == 0,
                '== 0',
            ),
            criterion('D3', 'tests_failing', unit_failures, lambda v: v == 0, '== 0'),
            criterion(
                'D3',
                'branch_coverage',
                val('coverage.branch_rate'),
                lambda v: v >= BRANCH_FLOOR,
                f'>= {BRANCH_FLOOR}',
            ),
            criterion(
                'D6',
                'image_within_ratchet',
                image,
                lambda v: v,
                'bytes <= infra/docker/app/image.json',
            ),
            criterion(
                'P3',
                'golden_pass',
                val('eval.golden_pass_rate'),
                lambda v: v == 1,
                '== 1.0',
            ),
        ]
    )
    for axis, names in PENDING.items():
        for name in names:
            criteria[f'{axis}.{name}'] = {
                'axis': axis,
                'status': 'unmet',
                'value': None,
                'rule': 'no collector yet',
            }
    return {
        'schema': 1,
        'generated': datetime.now(UTC).isoformat(timespec='seconds'),
        'metrics': m,
        'criteria': criteria,
        'judged': {
            'source': source,
            'scores': scores or None,
            'status': 'present' if source else 'not yet scored',
        },
    }


def image_within_cap(root: Path, m: dict) -> bool | None:
    """True when every measured image is within the committed size ratchet."""
    config = read_json(root / 'infra/docker/app/image.json') or {}
    checks = []
    for name in ('api', 'worker'):
        size, cap = m[f'image.{name}_bytes']['value'], config.get(f'{name}_max_bytes')
        if size is None or cap is None:
            return None
        checks.append(size <= cap)
    return all(checks)
