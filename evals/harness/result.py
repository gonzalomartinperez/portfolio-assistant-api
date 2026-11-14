"""Observation and grade value objects shared by the runner and the graders."""

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CitedSource:
    """One citation of the completed message; ``key`` is the canonical evidence key."""

    key: str
    url: str


@dataclass(frozen=True)
class RunResult:
    """What one scripted run produced (the last turn of an item).

    ``retrieved_keys`` and ``evidence_text`` are ``None`` when the run could not
    observe retrieval; graders that need them then fail closed.
    """

    answer: str
    events: tuple[str, ...] = ()
    citations: tuple[CitedSource, ...] = ()
    retrieved_keys: tuple[str, ...] | None = None
    evidence_text: str | None = None
    question: str = ''
    abstained: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    llm_calls: int = 0
    first_delta_ms: float | None = None
    total_ms: float | None = None
    terminal: str | None = None


# Section 11 limits of the stubbed and cassette lane.
DEFAULT_BUDGET: Mapping[str, float] = {
    'input_tokens': 6000,
    'output_tokens': 800,
    'llm_calls': 6,
    'first_delta_ms': 250,
    'total_ms': 1000,
}


@dataclass(frozen=True)
class GradingContext:
    """Per-run inputs that are not part of the observation."""

    canary: str | None = None
    prompt_text: str | None = None
    approved_urls: frozenset[str] = frozenset()
    budget: Mapping[str, float] = field(default_factory=lambda: DEFAULT_BUDGET)


@dataclass(frozen=True)
class GradeResult:
    """Verdict of one grader; ``detail`` never quotes the answer text."""

    name: str
    passed: bool
    detail: str = ''
