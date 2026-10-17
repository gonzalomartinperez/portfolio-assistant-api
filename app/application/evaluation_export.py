"""An explicitly requested synthetic evaluation summary, never a conversation trace."""

import re
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class EvaluationSummary:
    source_commit: str
    cases: int
    completed: int
    failed: int
    total_ms: int
    scope: Literal['synthetic_evaluation'] = 'synthetic_evaluation'

    def __post_init__(self) -> None:
        if not re.fullmatch(r'[a-f0-9]{40}', self.source_commit):
            raise ValueError('invalid evaluation revision')
        values = (self.cases, self.completed, self.failed, self.total_ms)
        if any(type(value) is not int for value in values):
            raise ValueError('evaluation counts must be integers')
        if (
            self.scope != 'synthetic_evaluation'
            or not 1 <= self.cases <= 10000
            or not 0 <= self.completed <= self.cases
            or not 0 <= self.failed <= self.cases
            or self.completed + self.failed != self.cases
            or not 0 <= self.total_ms <= 3600000
        ):
            raise ValueError('invalid synthetic evaluation summary')


class EvaluationExporter(Protocol):
    def export(self, summary: EvaluationSummary) -> bool: ...


def export_evaluation(
    summary: EvaluationSummary,
    *,
    authorized: bool,
    exporter: EvaluationExporter | None = None,
) -> Literal['disabled', 'exported', 'unavailable']:
    if not authorized:
        return 'disabled'
    if exporter is None:
        return 'unavailable'
    return 'exported' if exporter.export(summary) else 'unavailable'
