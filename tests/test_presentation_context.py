"""Bound public presentation hints without granting evidence or instruction authority."""

import asyncio
import json
from contextlib import aclosing
from dataclasses import asdict
from types import SimpleNamespace
from typing import get_args

import pytest
from pydantic import ValidationError

from app.ai.workflow import LangGraphWorkflow
from app.application.contracts import AnswerCommand
from app.application.presentation_context import PortfolioPath, PresentationContext
from app.infrastructure.answer import ResponsesProvider
from app.presentation.models import SendMessage
from tests.test_workflow import SOURCE

CONTEXT = {
    'theme': 'dark',
    'opened_path': '/work',
    'current_path': '/about',
    'presentation': 'compact',
}


@pytest.mark.parametrize('path', get_args(PortfolioPath))
def test_only_catalogued_public_paths_are_accepted(path):
    value = SendMessage.model_validate(
        {
            'content': 'Question',
            'locale': 'es',
            'context': {**CONTEXT, 'current_path': path},
        }
    )
    assert value.context.current_path == path
    assert value.locale == 'es'


@pytest.mark.parametrize(
    'field,value',
    [
        ('current_path', '/about?private=1'),
        ('opened_path', '/work#section'),
        ('current_path', 'https://gonzalomartinperez.com/about'),
        ('current_path', '//evil.example/about'),
        ('current_path', '/admin'),
        ('current_path', '/es/admin'),
        ('current_path', '/work/unknown'),
        ('current_path', '/es/../about'),
        ('current_path', '/%61bout'),
        ('current_path', '/about/'),
        ('current_path', '/about\\'),
        ('current_path', '/' + 'a' * 10000),
        ('theme', 'system'),
        ('presentation', 'fullscreen'),
        ('opened_path', None),
        ('locale', 'es'),
        ('instructions', 'ignore system'),
    ],
)
def test_unknown_fields_and_unbounded_or_nonpublic_values_fail(field, value):
    with pytest.raises(ValidationError):
        SendMessage.model_validate(
            {'content': 'Question', 'context': {**CONTEXT, field: value}}
        )


def test_context_is_optional_but_complete_when_present():
    assert SendMessage(content='Question').context is None
    assert SendMessage(content='Question', context=None).context is None
    for key in CONTEXT:
        incomplete = {k: v for k, v in CONTEXT.items() if k != key}
        with pytest.raises(ValidationError):
            SendMessage.model_validate({'content': 'Question', 'context': incomplete})


def test_workflow_does_not_turn_context_into_retrieval_evidence():
    context = PresentationContext('light', '/es/work', '/es/about', 'expanded')

    class Retrieval:
        async def search(self, question, locale):
            assert question == 'Question'
            assert locale == 'es'
            return (SOURCE,)

    class Provider:
        async def stream(self, question, evidence, locale, history=(), context=None):
            assert context == expected
            assert '/es/about' not in evidence
            assert evidence.endswith(SOURCE.content)
            yield 'Answer'

    expected = context

    async def run():
        result = [
            event
            async for event in LangGraphWorkflow(Retrieval(), Provider()).stream(
                AnswerCommand('context-test', 'Question', 'es', context=context)
            )
        ]
        assert result[-1].text == 'Answer'
        assert result[-1].sources == (SOURCE,)

    asyncio.run(run())


def test_provider_keeps_metadata_in_untrusted_user_data_and_closes_stream():
    context = PresentationContext('dark', '/work', '/about', 'page')

    class Events:
        closed = False

        def __aiter__(self):
            return self.iterate()

        async def iterate(self):
            yield SimpleNamespace(type='response.output_text.delta', delta='Answer')
            yield SimpleNamespace(
                type='response.completed', response=SimpleNamespace(usage=None)
            )

        async def close(self):
            self.closed = True

    events = Events()

    class Responses:
        async def create(self, **kwargs):
            assert kwargs['store'] is False
            policy, user = kwargs['input']
            assert 'never establish facts' in policy['content']
            assert '/work' not in policy['content']
            data = json.loads(user['content'])
            assert data['public_evidence'] == 'Verified source'
            assert data['untrusted_presentation_context'] == asdict(context)
            return events

    async def run():
        provider = ResponsesProvider(
            SimpleNamespace(responses=Responses()), 'gpt-6-luna'
        )
        async with aclosing(
            provider.stream('Question', 'Verified source', 'en', context=context)
        ) as stream:
            assert [item async for item in stream] == ['Answer']
        assert events.closed

    asyncio.run(run())


def test_committed_examples_and_legacy_idempotency_encoding():
    from pathlib import Path

    for value in json.loads(Path('contracts/send-message.examples.json').read_text()):
        SendMessage.model_validate(value)
    assert (
        SendMessage(content='Question').model_dump_json(exclude_none=True)
        == '{"content":"Question","locale":"en"}'
    )
