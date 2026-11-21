"""Run lifecycle, cancellation, output and public event policy."""

import asyncio
import logging
import re
from contextlib import aclosing
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Protocol
from uuid import UUID, uuid4

from portfolio_assistant.application.contracts import (
    AnswerCommand,
    Evidence,
    Workflow,
    WorkflowEvent,
)
from portfolio_assistant.application.conversation_context import Turn, bounded_history
from portfolio_assistant.application.observability import (
    Execution,
    ExecutionObserver,
    Outcome,
    Stage,
    measurements,
    phase,
    stage_origin,
)
from portfolio_assistant.domain.errors import (
    BudgetExhaustedError,
    DependencyUnavailableError,
    ProviderUnavailableError,
    RejectedError,
)
from portfolio_assistant.domain.messages import insufficient_message

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from collections.abc import AsyncGenerator, Callable

    from portfolio_assistant.application.clock import Clock
    from portfolio_assistant.application.presentation_context import PresentationContext


@dataclass(frozen=True)
class RunEvent:
    """A public v1 event name and payload, before HTTP encoding."""

    name: str
    payload: dict[str, object]


class RunStore(Protocol):
    """Atomic persisted transitions; unavailable storage raises DependencyUnavailableError."""

    async def start(self, run_id: UUID) -> bool:
        """Claim a pending run without reviving terminal states."""
        ...

    async def history(self, run_id: UUID, conversation_id: UUID) -> tuple[Turn, ...]:
        """Load bounded earlier turns only for this claimed run's conversation."""
        ...

    async def running(self, run_id: UUID) -> bool:
        """Check persisted cancellation while the provider may be silent."""
        ...

    async def complete(
        self,
        run_id: UUID,
        conversation_id: UUID,
        answer: str,
        citations: list[dict[str, object]],
    ) -> UUID | None:
        """Save the answer and terminal state atomically, unless already cancelled."""
        ...

    async def fail(self, run_id: UUID, code: str) -> bool:
        """Mark a live run failed; return false if it is already terminal or deleted."""
        ...

    async def interrupt(self, run_id: UUID) -> None:
        """Interrupt a still-live run after a lost stream; never overwrite terminal state."""
        ...


_MARKDOWN_REFERENCE = re.compile(r"```[\s\S]*?```|`[^`\n]*`|(?<![\w])\[([0-9]+)\](?!\()")


def referenced_sources(answer: str, count: int) -> tuple[int, ...]:
    used = {int(match[1]) for match in _MARKDOWN_REFERENCE.finditer(answer) if match[1]}
    if any(number < 1 or number > count for number in used):
        raise ValueError("invalid source reference")
    return tuple(sorted(used))


def normalize_citation_markers(answer: str, count: int) -> str:
    """Map prose markers to the compact citation list; leave code and links intact."""
    mapping = {source: index for index, source in enumerate(referenced_sources(answer, count), 1)}
    return _MARKDOWN_REFERENCE.sub(
        lambda match: f"[{mapping[int(match[1])]}]" if match[1] else match[0], answer
    )


def citations(
    sources: tuple[Evidence, ...],
    answer: str,
    citation_support: Callable[[str, str, str], bool] | None = None,
) -> list[dict[str, object]]:
    if citation_support is not None:
        if answer in (insufficient_message("en"), insufficient_message("es")):
            sources = ()
        else:
            # Fixture quotes identify actual excerpt support, not every retrieved candidate.
            sources = tuple(
                source
                for source in sources[:2]
                if citation_support(source.content, answer, source.path)
            )
    else:
        used = referenced_sources(answer, len(sources))
        sources = tuple(source for index, source in enumerate(sources, 1) if index in used)
    result: list[dict[str, object]] = []
    for source in sources:
        record = asdict(source)
        record["label"] = record.pop("title")
        record.pop("content")
        result.append(record)
    return result


@dataclass
class _RunOutput:
    """Collect the workflow's final answer and sources as progress is emitted."""

    answer: str = ""
    sources: tuple[Evidence, ...] = ()

    def apply(self, event: WorkflowEvent) -> RunEvent | None:
        """Retain finalization data and translate visible workflow updates."""
        if event.kind == "evidence":
            self.sources = event.sources
            return RunEvent(
                "run.status",
                {"phase": "evidence_found", "sources": len(self.sources)},
            )
        if event.kind == "delta":
            return RunEvent("message.delta", {"text": event.text})
        if event.kind == "answer":
            self.answer = event.text
        return None


class RunService:
    """Deliver bounded runs and reconcile cancellation with persisted state."""

    def __init__(
        self,
        store: RunStore,
        workflow: Workflow,
        *,
        fixture: bool,
        citation_support: Callable[[str, str, str], bool] | None = None,
        timeout_seconds: float = 60,
        observer: ExecutionObserver | None = None,
        clock: Clock,
    ):
        self.clock = clock
        if fixture != (citation_support is not None):
            raise ValueError("fixture mode requires citation_support, and only fixture mode")
        self.observer = observer
        self.store = store
        self.workflow = workflow
        self.fixture = fixture
        self.citation_support = citation_support
        self.timeout_seconds = timeout_seconds
        self._cleanup_tasks: set[asyncio.Task[None]] = set()
        self._active_runs: set[UUID] = set()

    async def drain_cleanup(self) -> None:
        """Keep storage open for interruption writes after ASGI cancellation."""
        # Lifespan can resume before nested stream generators reach their finally.
        for run_id in tuple(self._active_runs):
            self._schedule_interrupt(run_id)
        if self._cleanup_tasks:
            _, pending = await asyncio.wait(tuple(self._cleanup_tasks), timeout=5)
            if pending:
                logging.getLogger("portfolio_assistant").warning(
                    '{"operation":"run_cleanup","status":"lease_recovery_pending"}'
                )

    def _cleanup_finished(self, task: asyncio.Task[None]) -> None:
        self._cleanup_tasks.discard(task)
        if not task.cancelled():
            task.exception()

    def _schedule_interrupt(self, run_id: UUID) -> asyncio.Task[None]:
        async def interrupt() -> None:
            try:
                await self.store.interrupt(run_id)
            except DependencyUnavailableError:
                logging.getLogger("portfolio_assistant").warning(
                    '{"operation":"run_cleanup","status":"lease_recovery_pending"}'
                )

        cleanup = asyncio.create_task(interrupt())
        self._cleanup_tasks.add(cleanup)
        cleanup.add_done_callback(self._cleanup_finished)
        return cleanup

    async def execute(
        self,
        run_id: UUID,
        conversation_id: UUID,
        question: str,
        locale: str,
        context: PresentationContext | None = None,
    ) -> AsyncGenerator[RunEvent]:
        started_at = self.clock.now()
        started = perf_counter()
        first_token = None
        outcome: Outcome = "cancelled"
        error_code = None
        claimed = False
        stages: list[Stage] = []
        try:
            async with aclosing(
                self._execute(run_id, conversation_id, question, locale, context)
            ) as stream:
                while True:
                    token = measurements.set(stages if self.observer else None)
                    origin_token = stage_origin.set(started)
                    try:
                        event = await anext(stream)
                    except StopAsyncIteration:
                        break
                    finally:
                        measurements.reset(token)
                        stage_origin.reset(origin_token)
                    if event.name == "run.started":
                        claimed = True
                    elif event.name == "message.delta" and first_token is None:
                        first_token = (perf_counter() - started) * 1000
                    elif event.name == "run.completed":
                        outcome = "completed"
                    elif event.name == "run.failed":
                        outcome = "failed"
                        code = event.payload.get("code")
                        error_code = (
                            str(code)
                            if code
                            in {
                                "provider_unavailable",
                                "generation_failed",
                                "budget_exhausted",
                                "knowledge_updating",
                                "dependency_unavailable",
                            }
                            else "other"
                        )
                    yield event
        finally:
            if self.observer and claimed:
                execution = Execution(
                    uuid4().hex,
                    started_at,
                    outcome,
                    max(0, (perf_counter() - started) * 1000),
                    first_token,
                    tuple(stages),
                    error_code,
                )
                try:
                    self.observer.record(execution)
                except Exception:  # noqa: BLE001 - Observational failures must not change a paid run or expose adapter errors.
                    logging.getLogger("portfolio_assistant").warning(
                        '{"operation":"observability","status":"record_dropped"}'
                    )

    async def _execute(
        self,
        run_id: UUID,
        conversation_id: UUID,
        question: str,
        locale: str,
        context: PresentationContext | None = None,
    ) -> AsyncGenerator[RunEvent]:
        """Yield v1 events; cancel silent providers and never save partial answers."""
        output = _RunOutput()
        pending: asyncio.Task[WorkflowEvent] | None = None
        self._active_runs.add(run_id)
        try:
            if not await self.store.start(run_id):
                yield RunEvent("run.cancelled", {})
                return
            yield RunEvent("run.started", {"state": "running"})
            # An explicit deadline, not asyncio.timeout: the SSE heartbeat advances this
            # generator from a new task per event, and a timeout scope binds to one task.
            loop = asyncio.get_running_loop()
            deadline = loop.time() + self.timeout_seconds
            async with aclosing(
                self.workflow.stream(
                    AnswerCommand(
                        str(run_id),
                        question,
                        locale,
                        bounded_history(await self.store.history(run_id, conversation_id)),
                        context,
                    )
                )
            ) as stream:
                while True:
                    pending = asyncio.create_task(anext(stream))
                    try:
                        if not await self._wait_for_workflow(run_id, pending, loop, deadline):
                            pending.cancel()
                            await asyncio.gather(pending, return_exceptions=True)
                            yield RunEvent("run.cancelled", {})
                            return
                    except BaseException:
                        pending.cancel()
                        await asyncio.gather(pending, return_exceptions=True)
                        raise
                    try:
                        event = pending.result()
                    except StopAsyncIteration:
                        break
                    if (progress := output.apply(event)) is not None:
                        yield progress
            completed = await self._finalize(run_id, conversation_id, output)
            if completed is None:
                yield RunEvent("run.cancelled", {})
                return
            yield completed
            yield RunEvent("run.completed", {"state": "completed"})
        except Exception as error:  # noqa: BLE001 - Public stream fault boundary: preserve a terminal event without exposing internals.
            yield await self._failure_event(run_id, error)
        finally:
            # The cleanup task survives cancellation from an ASGI task-group scope.
            cleanup = self._schedule_interrupt(run_id)
            self._active_runs.discard(run_id)
            if pending and not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            await asyncio.shield(cleanup)

    async def _wait_for_workflow(
        self,
        run_id: UUID,
        pending: asyncio.Task[WorkflowEvent],
        loop: AbstractEventLoop,
        deadline: float,
    ) -> bool:
        """Poll persisted cancellation even when the upstream provider is silent."""
        while not pending.done():
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError("run deadline exceeded")
            await asyncio.wait({pending}, timeout=min(0.1, remaining))
            if not await self.store.running(run_id):
                return False
        return True

    async def _finalize(
        self, run_id: UUID, conversation_id: UUID, output: _RunOutput
    ) -> RunEvent | None:
        """Persist the canonical answer before exposing the completed message."""
        answer, sources = output.answer, output.sources
        with phase("finalization"):
            refs = citations(sources, answer, self.citation_support)
            if not self.fixture:
                answer = normalize_citation_markers(answer, len(sources))
            message_id = await self.store.complete(run_id, conversation_id, answer, refs)
        if message_id is None:
            return None
        return RunEvent(
            "message.completed",
            {"message_id": str(message_id), "content": answer, "citations": refs},
        )

    async def _failure_event(self, run_id: UUID, error: Exception) -> RunEvent:
        """Report a safe failure or honor a concurrent terminal transition."""
        code = (
            "budget_exhausted"
            if isinstance(error, BudgetExhaustedError)
            else "provider_unavailable"
            if isinstance(error, ProviderUnavailableError)
            else error.code
            if isinstance(error, RejectedError)
            else "generation_failed"
        )
        try:
            changed = await self.store.fail(run_id, code)
        except DependencyUnavailableError:
            # The persisted lease reconciles this run when storage recovers.
            changed = True
        return RunEvent("run.failed", {"code": code}) if changed else RunEvent("run.cancelled", {})
