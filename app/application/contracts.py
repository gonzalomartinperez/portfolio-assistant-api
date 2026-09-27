"""Framework-free contracts for a bounded answer workflow."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class Evidence:
    id: str
    title: str
    url: str
    source_type: str
    commit_sha: str
    path: str
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True)
class AnswerCommand:
    run_id: str
    question: str
    locale: str


@dataclass(frozen=True)
class WorkflowEvent:
    kind: Literal['evidence', 'delta', 'answer']
    text: str = ''
    sources: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


class Retrieval(Protocol):
    async def search(self, question: str, locale: str) -> tuple[Evidence, ...]: ...


class Provider(Protocol):
    def stream(
        self, question: str, evidence: str, locale: str
    ) -> AsyncGenerator[str | Usage]: ...


class Accounting(Protocol):
    async def reserve(self, run_id: str) -> None: ...
    async def settle(self, run_id: str, usage: Usage) -> None: ...


class Workflow(Protocol):
    def stream(self, command: AnswerCommand) -> AsyncGenerator[WorkflowEvent]: ...


class GenerationFailed(Exception):
    """A provider failed or exceeded the permitted output."""
