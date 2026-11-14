"""Eval reports: counts per stratum and locale; raw answer text never enters a report."""

import json
import os
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from evals.harness.result import GradeResult


@dataclass(frozen=True)
class ItemOutcome:
    item_id: str
    locale: str
    strata: tuple[str, ...]
    grades: tuple[GradeResult, ...]
    status: str = 'active'

    @property
    def passed(self) -> bool:
        return all(g.passed for g in self.grades)


def wilson_interval(passed: int, total: int, z: float = 1.96) -> list[float]:
    """Wilson score 95% interval for a pass rate; ``[0, 1]`` when there is no data."""
    if total == 0:
        return [0.0, 1.0]
    p = passed / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [round(max(0.0, centre - margin), 4), round(min(1.0, centre + margin), 4)]


def build_report(
    outcomes: Sequence[ItemOutcome],
    *,
    tier: str,
    run_id: str,
    pins: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Pure aggregation over the gate (active items); ``pins`` are recorded when known.

    Retired items are dropped and quarantined items are listed separately, outside
    every count. Each tally carries its pass rate and Wilson 95% interval.
    """

    def tally(rows: Sequence[ItemOutcome]) -> dict[str, object]:
        passed = sum(r.passed for r in rows)
        return {
            'total': len(rows),
            'passed': passed,
            'wilson95': wilson_interval(passed, len(rows)),
        }

    quarantined = {o.item_id: o.passed for o in outcomes if o.status == 'quarantined'}
    outcomes = [o for o in outcomes if o.status == 'active']

    by_locale: dict[str, list[ItemOutcome]] = defaultdict(list)
    by_stratum: dict[str, list[ItemOutcome]] = defaultdict(list)
    for outcome in outcomes:
        by_locale[outcome.locale].append(outcome)
        for stratum in outcome.strata:
            by_stratum[stratum].append(outcome)
    return {
        'tier': tier,
        'run_id': run_id,
        'pins': dict(pins or {}),
        'quarantined': dict(sorted(quarantined.items())),
        'totals': tally(outcomes),
        'by_locale': {k: tally(v) for k, v in sorted(by_locale.items())},
        'by_stratum': {
            stratum: {
                **tally(rows),
                'by_locale': {
                    loc: tally([r for r in rows if r.locale == loc])
                    for loc in sorted({r.locale for r in rows})
                },
            }
            for stratum, rows in sorted(by_stratum.items())
        },
        'failing_ids_by_stratum': {
            stratum: sorted(r.item_id for r in rows if not r.passed)
            for stratum, rows in sorted(by_stratum.items())
            if any(not r.passed for r in rows)
        },
        'failed_assertions': {
            o.item_id: [g.name for g in o.grades if not g.passed]
            for o in outcomes
            if not o.passed
        },
    }


def write_report(report: Mapping[str, object], directory: Path) -> Path:
    """Write ``<tier>-<run_id>.json`` with mode 0600; refuse to overwrite."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{report["tier"]}-{report["run_id"]}.json'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
        output.write(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
        )
    return path
