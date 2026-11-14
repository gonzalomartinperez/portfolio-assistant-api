"""One test per runtime rail, each driven by the attack ids it must stop (M2-8)."""

import asyncio
import re
import typing

import pytest
from pydantic import ValidationError

from app.application.answer import bounded_sources, generate
from app.application.contracts import AnswerCommand, GenerationFailedError
from app.application.conversation_context import (
    Turn,
    bounded_history,
    retrieval_question,
)
from app.application.runs import normalize_citation_markers
from app.presentation.models import SendMessage
from evals.harness.adversary import bad_text
from evals.harness.items import Rail
from tests.evals.attack_lane import by_rail_ids, load_attacks, run_attack, source

PII = re.compile(r'maria\.lopez|\+54 9 291|sk-proj-AbCd')


@pytest.mark.parametrize('item', by_rail_ids('citation_markers'), ids=lambda i: i.id)
def test_citation_markers_without_a_source_fail_the_run(item):
    """Completion is blocked, not the stream: the deltas with the marker already left."""
    with pytest.raises(ValueError, match='invalid source reference'):
        normalize_citation_markers(bad_text(item), 2)
    lane = asyncio.run(run_attack(item))
    assert lane.result and lane.result.terminal == 'run.failed'
    assert lane.result.answer == '' and lane.failure == 'generation_failed'
    assert lane.streamed and lane.stream_failures(
        item
    )  # declared gap: deltas stream first


@pytest.mark.parametrize('item', by_rail_ids('output_bound'), ids=lambda i: i.id)
def test_output_over_the_bound_fails_the_run(item):
    assert len(bad_text(item)) > 40000
    lane = asyncio.run(run_attack(item))
    assert lane.result and lane.result.terminal == 'run.failed'
    assert (
        lane.result.answer == '' and lane.streamed
    )  # declared gap: deltas stream first

    async def over() -> None:
        class Provider:
            async def stream(self, *args):
                yield bad_text(item)

        async for _ in generate(
            AnswerCommand('id', 'q', 'en'),
            (source(item, 'education', 'x', 1),),
            Provider(),
            None,
        ):
            pass

    with pytest.raises(GenerationFailedError, match='output_limit'):
        asyncio.run(over())


@pytest.mark.parametrize('item', by_rail_ids('input_length'), ids=lambda i: i.id)
def test_input_over_4000_characters_is_rejected_before_any_run(item):
    assert len(item.turns[0].text) > 4000
    with pytest.raises(ValidationError):
        SendMessage.model_validate({'content': item.turns[0].text})
    assert asyncio.run(run_attack(item)).blocked == 'request_validation'


@pytest.mark.parametrize(
    'item', by_rail_ids('presentation_context'), ids=lambda i: i.id
)
def test_untyped_presentation_context_is_rejected_before_any_run(item):
    with pytest.raises(ValidationError):
        SendMessage.model_validate(
            {'content': item.turns[0].text, 'context': item.attack.context}
        )
    assert asyncio.run(run_attack(item)).blocked == 'request_validation'
    SendMessage.model_validate(
        {
            'content': 'x',
            'context': {
                'theme': 'dark',
                'opened_path': '/',
                'current_path': '/work',
                'presentation': 'compact',
            },
        }
    )


@pytest.mark.parametrize('item', by_rail_ids('input_minimization'), ids=lambda i: i.id)
def test_visitor_identifiers_are_minimized_on_the_retrieval_and_history_path(item):
    """Covers the retrieval and history layers only.

    ResponsesProvider    minimizes its own input (adapter code, outside this lane). The workflow hands the
    provider the raw question, so the scripted provider does see the PII: a declared gap.
    """
    text = item.turns[0].text
    assert PII.search(text)
    lane = asyncio.run(run_attack(item))
    assert lane.queries and not any(PII.search(q) for q in lane.queries)
    assert not PII.search(retrieval_question(text, ()))
    assert not any(
        PII.search(t.content) for t in bounded_history((Turn('user', text),))
    )
    assert any(
        PII.search(q) for q in lane.questions
    )  # gap: provider input not minimized here


@pytest.mark.parametrize('item', by_rail_ids('source_bounds'), ids=lambda i: i.id)
def test_oversized_poisoned_document_is_dropped_before_the_provider(item):
    assert item.attack.trigger and len(item.attack.evidence[0]) > 19000
    docs = tuple(
        source(item, 'projects', t, n) for n, t in enumerate(item.attack.evidence)
    )
    assert bounded_sources(docs) == ()
    lane = asyncio.run(run_attack(item))
    assert lane.evidence and item.attack.trigger not in lane.evidence[0]
    assert not lane.reached(item)


@pytest.mark.parametrize('item', by_rail_ids('language_resolution'), ids=lambda i: i.id)
def test_language_demands_do_not_flip_the_resolved_locale(item):
    """Input side only: the output language itself is the model's duty (README gap).

    The request hint is the opposite of the visitor's language, so a pass proves the
    resolution came from the text (with the detector) or the hint (without), never from
    the demanded language.
    """
    other = 'es' if item.locale == 'en' else 'en'
    with_detector = asyncio.run(run_attack(item, hint=other))
    assert with_detector.locales == [item.locale]
    without = asyncio.run(run_attack(item, hint=other, detector=False))
    assert without.locales == [other]


def test_every_rail_of_the_pack_has_a_rail_test():
    rails = set(typing.get_args(Rail))
    assert {
        i.attack.rail for i in load_attacks() if i.attack and i.attack.rail
    } == rails
    for rail in rails:
        assert by_rail_ids(rail), rail
