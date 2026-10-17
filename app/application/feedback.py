"""Read-only, content-free signals for human review; no training operation."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FeedbackSummary:
    observed_at: str
    up: int
    down: int


class FeedbackReadPort(Protocol):
    def read(self) -> FeedbackSummary: ...
