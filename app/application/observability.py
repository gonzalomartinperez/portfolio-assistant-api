"""Bounded operational measurements; never accept conversation text or identifiers."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Literal, Protocol

Phase = Literal[
    'language', 'vector_retrieval', 'graph_retrieval', 'generation', 'finalization'
]
Outcome = Literal['completed', 'cancelled', 'failed']


@dataclass(frozen=True)
class Stage:
    name: Phase
    duration_ms: float
    start_offset_ms: float = 0


@dataclass(frozen=True)
class Execution:
    trace_id: str
    started_at: datetime
    outcome: Outcome
    duration_ms: float
    first_token_ms: float | None
    stages: tuple[Stage, ...]
    error_code: str | None


class ExecutionObserver(Protocol):
    def record(self, execution: Execution) -> None:
        """Enqueue without network I/O or waiting on the conversation path."""
        ...


stage_origin: ContextVar[float | None] = ContextVar('stage_origin', default=None)

measurements: ContextVar[list[Stage] | None] = ContextVar('measurements', default=None)


@contextmanager
def phase(name: Phase) -> Iterator[None]:
    stages = measurements.get()
    if stages is None:
        yield
        return
    started = perf_counter()
    try:
        yield
    finally:
        if len(stages) < 32:
            stages.append(
                Stage(
                    name,
                    max(0, (perf_counter() - started) * 1000),
                    max(0, (started - (stage_origin.get() or started)) * 1000),
                )
            )
