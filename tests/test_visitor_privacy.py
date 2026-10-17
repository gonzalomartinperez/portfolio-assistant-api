"""Minimize outbound context without rejecting normal volunteered information."""

import asyncio
import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.application.conversation_context import (
    Turn,
    bounded_history,
    retrieval_question,
)
from app.domain.privacy import minimize_visitor_text
from app.infrastructure.answer import ResponsesProvider
from app.presentation.models import SendMessage


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        (
            'Contact me at candidate@example.invalid about React.',
            'Contact me at (email) about React.',
        ),
        (
            'Mi número es +54 9 291 555-0134. Quiero hablar de Filomena.',
            'Mi número es (phone). Quiero hablar de Filomena.',
        ),
        ('My number is +1 (202) 555-0134.', 'My number is (phone).'),
        (
            'Experience: 2021-2025, 18 projects and +15% improvement.',
            'Experience: 2021-2025, 18 projects and +15% improvement.',
        ),
        ('a@b.co', '(…)'),
        (
            'Explain PostgreSQL 18.6 and Python 3.14.8.',
            'Explain PostgreSQL 18.6 and Python 3.14.8.',
        ),
    ],
)
def test_common_identifiers_minimize_idempotently_without_increasing_bounds(
    text, expected
):
    result = minimize_visitor_text(text)
    assert result == expected
    assert minimize_visitor_text(result) == result
    assert len(result) <= len(text)
    assert len(result.encode()) <= len(text.encode())


def test_key_patterns_and_followups_are_minimized_but_input_is_not_rejected():
    key = 'sk-' + 'x' * 40
    content = 'I use React; email candidate@example.invalid and ' + key
    assert SendMessage(content=content, locale='en').content == content
    minimized = minimize_visitor_text(content)
    assert key not in minimized and '(secret)' in minimized
    assert minimize_visitor_text('Bearer ' + 'A' * 32) == '(secret)'
    history = bounded_history(
        (Turn('user', content), Turn('assistant', 'Public React experience.'))
    )
    query = retrieval_question('Can you explain that?', history)
    assert (
        'React' in query
        and 'candidate@example.invalid' not in query
        and key not in query
    )
    assert sum(len(turn.content) for turn in history) <= 8000


@pytest.mark.parametrize('locale', ['en', 'es'])
def test_real_sdk_sends_minimized_context_and_unchanged_public_evidence(locale):
    captured = []
    email = 'candidate@example.invalid'
    phone = '+1 (202) 555-0134'
    evidence = 'PUBLIC SOURCE [1]: Public contact is public-profile@example.invalid. Documented React experience.'

    def handle(request):
        captured.append(json.loads(request.content))
        frames = [
            {
                'type': 'response.output_text.delta',
                'sequence_number': 1,
                'item_id': 'msg_fixture',
                'output_index': 0,
                'content_index': 0,
                'delta': 'Documented profile [1].',
            },
            {
                'type': 'response.completed',
                'sequence_number': 2,
                'response': {
                    'id': 'resp_fixture',
                    'object': 'response',
                    'created_at': 1,
                    'model': 'gpt-6-luna',
                    'status': 'completed',
                    'output': [],
                    'usage': {
                        'input_tokens': 12,
                        'output_tokens': 8,
                        'total_tokens': 20,
                    },
                },
            },
        ]
        body = ''.join('data: ' + json.dumps(frame) + '\n\n' for frame in frames)
        return httpx.Response(
            200, headers={'Content-Type': 'text/event-stream'}, content=body
        )

    async def run():
        async with AsyncOpenAI(
            api_key='synthetic-fixture-only',
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
        ) as client:
            provider = ResponsesProvider(client, 'gpt-6-luna')
            output = [
                item
                async for item in provider.stream(
                    f'React role. {email}',
                    evidence,
                    locale,
                    (Turn('user', f'Contact {phone}'),),
                )
            ]
            assert output[0] == 'Documented profile [1].'

    asyncio.run(run())
    assert len(captured) == 1
    request = captured[0]
    assert request['store'] is False and request['model'] == 'gpt-6-luna'
    assert request['reasoning'] == {'effort': 'medium'}
    encoded = json.dumps(request['input'])
    assert email not in encoded and phone not in encoded
    payload = json.loads(request['input'][1]['content'])
    assert payload['public_evidence'] == evidence
    assert '(email)' in payload['question']
    assert '(phone)' in payload['untrusted_conversation'][0]['content']
    instructions = request['input'][0]['content']
    assert (
        'without scolding' in instructions
        and 'does not train you or update the corpus' in instructions
    )
