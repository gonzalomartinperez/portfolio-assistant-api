"""Offline deterministic lane: the real workflow and run service with in-memory fakes.

It mirrors production composition (``fixture=False``, language detector wired) and skips
only HTTP, sessions and the stores, so the PR lane covers every rail without databases.
"""

from dataclasses import dataclass, field, replace
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from app.adapters.providers.language import LocalLanguageDetector
from app.ai.workflow import LangGraphWorkflow
from app.application.contracts import Evidence
from app.application.runs import RunService
from app.presentation.models import SendMessage
from evals.harness.adversary import GRADING, AdversarialProvider
from evals.harness.graders import grade_item
from evals.harness.items import Item
from evals.harness.loader import load_items
from evals.harness.result import GradeResult, RunResult
from evals.harness.runner import RecordingProvider, collect, item_context
from tests.test_workflow import Store

ATTACKS = Path(__file__).resolve().parents[2] / 'evals' / 'attacks'


def load_attacks() -> list[Item]:
    return load_items(ATTACKS / 'attacks.jsonl')


def source(item: Item, topic: str, text: str, number: int) -> Evidence:
    path = f'src/content/{item.locale}/{topic}.ts'
    return Evidence(
        str(number),
        topic,
        'https://github.com/gonzalomartinperez/portfolio/blob/' + 'a' * 40 + '/' + path,
        'code',
        'a' * 40,
        path,
        1,
        5,
        text,
    )


@dataclass
class Lane:
    """What one attack produced; ``blocked`` names a rail that stopped it."""

    blocked: str | None = None
    result: RunResult | None = None
    queries: list[str] = field(default_factory=list)
    locales: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    failure: str | None = None

    questions: list[str] = field(default_factory=list)
    streamed: str = ''

    def _failures(self, item: Item, result: RunResult) -> list[GradeResult]:
        ctx = item_context(item, result, GRADING)
        return [g for g in grade_item(item, result, ctx) if not g.passed]

    def final_failures(self, item: Item) -> list[GradeResult]:
        """Failed graders over the completed message (empty if the run did not complete)."""
        if self.result is None or self.result.terminal != 'run.completed':
            return []
        return self._failures(item, self.result)

    def stream_failures(self, item: Item) -> list[GradeResult]:
        """Failed graders over the ``message.delta`` text a live-rendering client saw.

        Deltas leave before the finalization rails run, so this can be non-empty for a
        run that later fails and is never persisted.
        """
        if self.result is None or not self.streamed:
            return []
        return self._failures(item, replace(self.result, answer=self.streamed))

    def reached(self, item: Item) -> list[GradeResult]:
        """Failed graders on what the visitor saw: the stream or the final message."""
        return [*self.stream_failures(item), *self.final_failures(item)]


async def run_attack(
    item: Item, *, hint: str | None = None, detector: bool = True
) -> Lane:
    attack = item.attack
    assert attack is not None
    payload: dict[str, object] = {
        'content': item.turns[-1].text,
        'locale': item.locale,
    }
    if attack.context is not None:
        payload['context'] = attack.context
    try:
        message = SendMessage.model_validate(payload)
    except ValidationError:
        return Lane(blocked='request_validation')
    sources = (
        source(item, 'education', 'Universidad Nacional del Sur', 1),
        *(
            source(item, 'projects', text, number)
            for number, text in enumerate(attack.evidence, 2)
        ),
    )
    lane = Lane()

    class Retrieval:
        async def search(self, question: str, locale: str) -> tuple[Evidence, ...]:
            lane.queries.append(question)
            return sources

    provider = AdversarialProvider(item)
    recorder = RecordingProvider(provider)
    workflow = LangGraphWorkflow(
        Retrieval(), recorder, detector=LocalLanguageDetector() if detector else None
    )
    store = Store()
    service = RunService(store, workflow, fixture=False)
    events = [
        (event.name, {'type': event.name, 'payload': event.payload})
        async for event in service.execute(
            uuid4(), uuid4(), message.content, hint or item.locale
        )
    ]
    lane.locales = provider.locales
    lane.questions = provider.questions
    lane.streamed = ''.join(
        str(data['payload']['text']) for name, data in events if name == 'message.delta'
    )
    lane.evidence = recorder.evidence
    lane.failure = store.failure
    lane.result = collect(
        events,
        question=message.content,
        evidence=recorder.evidence,
        usage=recorder.usage,
        first_delta_ms=1.0,
        total_ms=1.0,
    )
    return lane


def by_rail_ids(rail: str) -> list[Item]:
    return [i for i in load_attacks() if i.attack and i.attack.rail == rail]
