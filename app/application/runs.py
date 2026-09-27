"""Run lifecycle, cancellation, output and public event policy."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import asdict, dataclass
from typing import Protocol
from uuid import UUID

from app.application.contracts import AnswerCommand, Evidence, Workflow, WorkflowEvent
from app.application.conversation_context import Turn, bounded_history
from app.domain.errors import BudgetExhaustedError, DependencyUnavailableError
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

    async def execute(
        self, run_id: UUID, conversation_id: UUID, question: str, locale: str
    ) -> AsyncGenerator[RunEvent]:
        """Yield v1 events; cancel silent providers and never save partial answers."""
        answer = ''
        sources: tuple[Evidence, ...] = ()
        pending: asyncio.Task[WorkflowEvent] | None = None
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
            if pending and not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)

            # The cleanup task survives cancellation from an ASGI task-group scope.
            async def interrupt() -> None:
                try:
                    await self.store.interrupt(run_id)
                except DependencyUnavailableError:
                    logging.getLogger('portfolio_assistant').warning(
                        '{"operation":"run_cleanup","status":"lease_recovery_pending"}'
                    )

            cleanup = asyncio.create_task(interrupt())
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                # Keep a strong reference until completion; SQL has its own timeout.
                cleanup.add_done_callback(
                    lambda task: task.exception() if not task.cancelled() else None
                )
                raise
