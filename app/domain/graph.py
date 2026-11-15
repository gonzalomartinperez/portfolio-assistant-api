"""Graph fact value object shared by projection adapters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fact:
    subject_kind: str
    subject: str
    predicate: str
    object_kind: str
    object: str
    start_line: int
    end_line: int
