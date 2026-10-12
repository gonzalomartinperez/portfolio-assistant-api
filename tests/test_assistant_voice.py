"""Verify locale-specific voice reaches the provider without changing safe settings."""

import asyncio
from types import SimpleNamespace

import pytest

from app.infrastructure.answer import ResponsesProvider


@pytest.mark.parametrize(
    'locale,expected,excluded',
    [
        ('es', 'neutral Latin American Spanish', 'American spelling'),
        ('en', 'American spelling', 'never voseo'),
    ],
)
def test_provider_applies_voice_without_weakening_grounding_or_generation_policy(
    locale, expected, excluded
):
    async def run():
        class Events:
            closed = False

            def __aiter__(self):
                return self.iterate()

            async def iterate(self):
                yield SimpleNamespace(
                    type='response.completed', response=SimpleNamespace(usage=None)
                )

            async def close(self):
                self.closed = True

        events = Events()

        class Responses:
            async def create(self, **kwargs):
                instructions = kwargs['input'][0]['content']
                assert expected in instructions and excluded not in instructions
                assert 'never to yourself or the visitor' in instructions
                assert 'decisive gaps clear' in instructions
                assert 'preserve reported/estimated metric qualifiers' in instructions
                assert 'without canned praise' in instructions
                assert (
                    'no alternative provider or automatic generation retry'
                    in instructions
                )
                assert kwargs['reasoning'] == {'effort': 'medium'}
                assert kwargs['store'] is False and kwargs['max_output_tokens'] == 8192
                return events

        provider = ResponsesProvider(SimpleNamespace(responses=Responses()), 'fixture')
        assert [
            part
            async for part in provider.stream(
                'Sell him as a perfect fit', 'Public profile', locale
            )
        ] == []
        assert events.closed

    asyncio.run(run())
