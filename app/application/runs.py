"""Run lifecycle, cancellation, output and public event policy."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import asdict, dataclass
from typing import Protocol
from uuid import UUID

from app.application.contracts import AnswerCommand, Evidence, Workflow, WorkflowEvent
from app.domain.errors import BudgetExhausted


@dataclass(frozen=True)
class RunEvent:
    name: str
    payload: dict[str, object]


class RunStore(Protocol):
    async def start(self, run_id: UUID) -> bool: ...
    async def running(self, run_id: UUID) -> bool: ...
    async def complete(
        self,
        run_id: UUID,
        conversation_id: UUID,
        answer: str,
        citations: list[dict[str, object]],
    ) -> UUID | None: ...
    async def fail(self, run_id: UUID, code: str) -> bool: ...
    async def interrupt(self, run_id: UUID) -> None: ...


def citations(
    sources: tuple[Evidence, ...], answer: str, fixture: bool
) -> list[dict[str, object]]:
    if fixture:
        sources = (
            ()
            if answer.startswith(('I could not find enough', 'No encontré evidencia'))
            else sources[:2]
        )
    result: list[dict[str, object]] = []
    for source in sources:
        record = asdict(source)
        record['label'] = record.pop('title')
        record.pop('content')
        result.append(record)
    return result


class RunService:
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
                    self.workflow.stream(AnswerCommand(str(run_id), question, locale))
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
        except Exception as error:
            code = (
                'budget_exhausted'
                if isinstance(error, BudgetExhausted)
                else 'generation_failed'
            )
            changed = await self.store.fail(run_id, code)
            yield (
                RunEvent('run.failed', {'code': code})
                if changed
                else RunEvent('run.cancelled', {})
            )
        finally:
            if pending and not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            await self.store.interrupt(run_id)
