"""budget_respected: section 11 limits for one run."""

from evals.harness.items import Item
from evals.harness.result import GradeResult, GradingContext, RunResult

_CONTEXT = GradingContext()
_METRICS = ('input_tokens', 'output_tokens', 'llm_calls', 'first_delta_ms', 'total_ms')


def budget_respected(
    item: Item, result: RunResult, ctx: GradingContext | None = None
) -> GradeResult:
    """Every budgeted metric is observed and within its limit (missing data fails)."""
    ctx = ctx or _CONTEXT
    problems = []
    for name, limit in ctx.budget.items():
        if name not in _METRICS:
            problems.append(f'unknown budget key {name}')
            continue
        value = getattr(result, name)
        if value is None:
            problems.append(f'{name} not observed')
        elif value > limit:
            problems.append(f'{name} {value} > {limit}')
    return GradeResult('budget_respected', not problems, '; '.join(problems) or 'ok')
