"""Framework-free contracts for a bounded answer workflow."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Literal, Protocol

from app.application.conversation_context import Turn


@dataclass(frozen=True)
class Evidence:
    """Verified public span with an immutable revision and stable citation target."""

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
    """Server-authorized input for one bounded answer run."""

    run_id: str
    question: str
    locale: str
    history: tuple[Turn, ...] = ()


@dataclass(frozen=True)
class WorkflowEvent:
    """Intentionally public workflow progress, excluding framework state and prompts."""

    kind: Literal['evidence', 'delta', 'answer']
    text: str = ''
    sources: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class Usage:
    """Provider-reported token counts; absence never implies a refund."""

    input_tokens: int
    output_tokens: int


class Retrieval(Protocol):
    """Read-only access to bounded, verified public evidence."""

    async def search(self, question: str, locale: str) -> tuple[Evidence, ...]:
        """Return at most five evidence spans for the requested language."""
        ...


class Provider(Protocol):
    """Incremental answer generation without assistant tools or authorization decisions."""

    def stream(
        self, question: str, evidence: str, locale: str, history: tuple[Turn, ...] = ()
    ) -> AsyncGenerator[str | Usage]:
        """Yield incremental text and final usage; closing cancels upstream work."""
        ...


class Accounting(Protocol):
    """Atomic reservation and settlement of potentially incurred model costs."""

    async def reserve(self, run_id: str) -> None:
        """Reserve the maximum permitted cost atomically before calling the provider."""
        ...

    async def settle(self, run_id: str, usage: Usage) -> None:
        """Record known token usage without refunding an unknown or interrupted call."""
        ...


class Workflow(Protocol):
    """Framework-independent boundary for evidence, text deltas and completed answers."""

    def stream(self, command: AnswerCommand) -> AsyncGenerator[WorkflowEvent]:
        """Yield public progress and answer events; propagate cancellation upstream."""
        ...


class GenerationFailedError(Exception):
    """A provider failed or exceeded the permitted output."""
