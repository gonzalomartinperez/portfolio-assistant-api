"""Cost and latency budgets (assistant-quality.md section 11) as a pure check.

``limits`` are the declared ceilings. ``measured`` holds the first recorded baseline per
metric (empty until the first replay); once present, a value more than 20% above it is a
regression, even when it is still under the declared ceiling. A change may only exceed
either with an approved ``budget-change`` ADR, which edits this file.
"""

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

REGRESSION_FACTOR = 1.2
BASELINE_PATH = Path('evals/baselines/budgets.json')


def p95(values: Sequence[float]) -> float:
    """Nearest-rank 95th percentile."""
    if not values:
        raise ValueError('no samples')
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def load_budgets(path: Path = BASELINE_PATH) -> dict[str, dict[str, float]]:
    raw = json.loads(path.read_text(encoding='utf-8'))
    limits = raw['limits']
    measured = raw.get('measured', {})
    if not limits or any(
        not isinstance(v, int | float) or v <= 0 for v in limits.values()
    ):
        raise ValueError('budget limits must be positive numbers')
    if not set(measured) <= set(limits):
        raise ValueError('measured baseline names an undeclared metric')
    return {'limits': dict(limits), 'measured': dict(measured)}


def check_budgets(
    observed: Mapping[str, float], budgets: Mapping[str, Mapping[str, float]]
) -> list[str]:
    """Return one violation per metric over its ceiling or 20% over its baseline.

    A declared metric missing from ``observed`` is a violation (fail closed); metrics
    that are observed but not declared are ignored.
    """
    problems = []
    limits, measured = budgets['limits'], budgets.get('measured', {})
    for name, limit in limits.items():
        if name not in observed:
            problems.append(f'{name}: not observed')
            continue
        value = observed[name]
        if value > limit:
            problems.append(f'{name}: {value} exceeds the declared limit {limit}')
        baseline = measured.get(name)
        if baseline is not None and value > baseline * REGRESSION_FACTOR:
            problems.append(
                f'{name}: {value} regressed more than 20% from the baseline {baseline}'
            )
    return problems
