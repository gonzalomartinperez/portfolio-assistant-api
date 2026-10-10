"""Run lifecycle, cancellation, output and public event policy."""

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import asdict, dataclass
from typing import Protocol
from uuid import UUID

from app.application.contracts import AnswerCommand, Evidence, Workflow, WorkflowEvent
from app.application.conversation_context import Turn, bounded_history
from app.application.presentation_context import PresentationContext
from app.domain.errors import (
    BudgetExhaustedError,
    DependencyUnavailableError,
    ProviderUnavailableError,
    RejectedError,
)
from app.domain.fixture import fixture_supports


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


_MARKDOWN_REFERENCE = re.compile(
    r'```[\s\S]*?```|`[^`\n]*`|(?<![\w])\[([0-9]+)\](?!\()'
)


def referenced_sources(answer: str, count: int) -> tuple[int, ...]:
    used = {int(match[1]) for match in _MARKDOWN_REFERENCE.finditer(answer) if match[1]}
    if any(number < 1 or number > count for number in used):
        raise ValueError('invalid source reference')
    return tuple(sorted(used))


def normalize_citation_markers(answer: str, count: int) -> str:
    """Map prose markers to the compact citation list; leave code and links intact."""
    mapping = {
        source: index
        for index, source in enumerate(referenced_sources(answer, count), 1)
    }
    return _MARKDOWN_REFERENCE.sub(
        lambda match: f'[{mapping[int(match[1])]}]' if match[1] else match[0], answer
    )


def citations(
    sources: tuple[Evidence, ...], answer: str, fixture: bool
) -> list[dict[str, object]]:
    if fixture:
        if answer.startswith(('I could not find enough', 'No encontré evidencia')):
            sources = ()
        else:
            # Fixture quotes identify actual excerpt support, not every retrieved candidate.
            sources = tuple(
                source
                for source in sources[:2]
                if fixture_supports(source.content, answer, source.path)
            )
    else:
        used = referenced_sources(answer, len(sources))
        sources = tuple(
            source for index, source in enumerate(sources, 1) if index in used
        )
    result: list[dict[str, object]] = []
    for source in sources:
        record = asdict(source)
        record['label'] = record.pop('title')
        record.pop('content')
        result.append(record)
    return result


class RunService:
    """Deliver bounded runs and reconcile cancellation with persisted state."""

    def __init__(
        self,
        store: RunStore,
        workflow: Workflow,
        *,
        fixture: bool,
        timeout_seconds: float = 60,
    ):
        self.store = store
        self.workflow = workflow
        self.fixture = fixture
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
                logging.getLogger('portfolio_assistant').warning(
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
                logging.getLogger('portfolio_assistant').warning(
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
        """Yield v1 events; cancel silent providers and never save partial answers."""
        answer = ''
        sources: tuple[Evidence, ...] = ()
        pending: asyncio.Task[WorkflowEvent] | None = None
        self._active_runs.add(run_id)
        try:
            if not await self.store.start(run_id):
                yield RunEvent('run.cancelled', {})
                return
            yield RunEvent('run.started', {'state': 'running'})
            async with asyncio.timeout(self.timeout_seconds):
                async with aclosing(
                    self.workflow.stream(
                        AnswerCommand(
                            str(run_id),
                            question,
                            locale,
                            bounded_history(
                                await self.store.history(run_id, conversation_id)
                            ),
                            context,
                        )
                    )
                ) as stream:
                    while True:
                        pending = asyncio.create_task(anext(stream))
                        # Poll persisted cancellation even while the upstream provider is silent.
                        try:
                            while not pending.done():
                                await asyncio.wait({pending}, timeout=0.1)
                                if not await self.store.running(run_id):
                                    pending.cancel()
                                    await asyncio.gather(
                                        pending, return_exceptions=True
                                    )
                                    yield RunEvent('run.cancelled', {})
                                    return
                        except BaseException:
                            pending.cancel()
                            await asyncio.gather(pending, return_exceptions=True)
                            raise
                        try:
                            event = pending.result()
                        except StopAsyncIteration:
                            break
                        if event.kind == 'evidence':
                            sources = event.sources
                            yield RunEvent(
                                'run.status',
                                {'phase': 'evidence_found', 'sources': len(sources)},
                            )
                        elif event.kind == 'delta':
                            yield RunEvent('message.delta', {'text': event.text})
                        elif event.kind == 'answer':
                            answer = event.text
            refs = citations(sources, answer, self.fixture)
            if not self.fixture:
                answer = normalize_citation_markers(answer, len(sources))
            message_id = await self.store.complete(
                run_id, conversation_id, answer, refs
            )
            if message_id is None:
                yield RunEvent('run.cancelled', {})
                return
            yield RunEvent(
                'message.completed',
                {'message_id': str(message_id), 'content': answer, 'citations': refs},
            )
            yield RunEvent('run.completed', {'state': 'completed'})
        except Exception as error:  # noqa: BLE001 - Public stream fault boundary: preserve a terminal event without exposing internals.
            code = (
                'budget_exhausted'
                if isinstance(error, BudgetExhaustedError)
                else 'provider_unavailable'
                if isinstance(error, ProviderUnavailableError)
                else error.code
                if isinstance(error, RejectedError)
                else 'generation_failed'
            )
            try:
                changed = await self.store.fail(run_id, code)
            except DependencyUnavailableError:
                # The persisted lease reconciles this run when storage recovers.
                changed = True
            yield (
                RunEvent('run.failed', {'code': code})
                if changed
                else RunEvent('run.cancelled', {})
            )
        finally:
            # The cleanup task survives cancellation from an ASGI task-group scope.
            cleanup = self._schedule_interrupt(run_id)
            self._active_runs.discard(run_id)
            if pending and not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            await asyncio.shield(cleanup)
