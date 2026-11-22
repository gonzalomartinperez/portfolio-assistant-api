"""Evidence framing and streamed answer policy at the provider boundary."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import replace
from unittest.mock import Mock

import pytest

from portfolio_assistant.application.answer import bounded_sources, context, generate
from portfolio_assistant.application.contracts import (
    Accounting,
    AnswerCommand,
    GenerationFailedError,
    Provider,
    Usage,
)
from portfolio_assistant.application.conversation_context import Turn
from portfolio_assistant.application.presentation_context import PresentationContext
from portfolio_assistant.domain.errors import BudgetExhaustedError
from tests.support_app import SOURCE, FakeAccounting


async def provider_items(*items: str | Usage) -> AsyncGenerator[str | Usage]:
    for item in items:
        yield item


def test_evidence_window_keeps_only_the_first_five_ranked_sources():
    sources = tuple(replace(SOURCE, id=str(index), path=f"source-{index}.md") for index in range(6))

    assert bounded_sources(sources) == sources[:5]
    assert "PUBLIC SOURCE [5] source-4.md" in context(sources)
    assert "source-5.md" not in context(sources)


def test_evidence_window_skips_a_source_that_would_exceed_the_budget_by_one():
    # With the path and framing allowance, the first span needs 19,001 characters.
    oversized = replace(SOURCE, content="a" * 18_892)

    assert bounded_sources((oversized, SOURCE)) == (SOURCE,)


def test_evidence_window_keeps_two_spans_that_fill_the_budget_exactly():
    first = replace(SOURCE, content="a" * 9_000)
    second = replace(SOURCE, content="b" * 9_782)

    assert bounded_sources((first, second, SOURCE)) == (first, second)


def test_default_evidence_context_uses_numbered_spans_without_canonical_urls():
    second = replace(SOURCE, path="docs/api.md", start_line=7, end_line=9, content="API overview")

    assert context((SOURCE, second)) == (
        "PUBLIC SOURCE [1] README.md lines 1-2:\nStub\n"
        "PUBLIC SOURCE [2] docs/api.md lines 7-9:\nAPI overview"
    )


@pytest.mark.parametrize(
    ("question", "locale", "source_header"),
    [
        ("Share the LINKS", "en", "README.md lines 1-2 canonical_url=https://example.test"),
        ("Dame el C\u00d3DIGO", "es", "README.md lines 1-2 canonical_url=https://example.test"),
        ("What was the leadership scope?", "en", "README.md lines 1-2"),
    ],
    ids=["english-links", "spanish-code", "ordinary-question"],
)
def test_provider_receives_authorized_context_and_urls_for_explicit_requests(
    question, locale, source_header
):
    async def run():
        history = (Turn("user", "Tell me about the portfolio."),)
        presentation = PresentationContext("dark", "/work", "/assistant", "compact")
        command = AnswerCommand("answer-run", question, locale, history, presentation)
        provider = Mock(spec=Provider)
        provider.stream.return_value = provider_items("Answer")

        assert [text async for text in generate(command, (SOURCE,), provider, None)] == ["Answer"]
        provider.stream.assert_called_once_with(
            question, f"PUBLIC SOURCE [1] {source_header}:\nStub", locale, history, presentation
        )

    asyncio.run(run())


def test_grounded_generation_reserves_and_settles_usage_for_the_same_run():
    async def run():
        provider = Mock(spec=Provider)
        accounting = Mock(spec=Accounting, wraps=FakeAccounting())
        usage = Usage(123, 45, "fixture-prompt")
        provider.stream.return_value = provider_items("First ", "second.", usage)
        command = AnswerCommand("costed-run", "Tell me about the API.", "en")

        async with aclosing(generate(command, (SOURCE,), provider, accounting)) as stream:
            assert await anext(stream) == "First "
            accounting.reserve.assert_awaited_once_with("costed-run")
            accounting.settle.assert_not_awaited()
            assert [text async for text in stream] == ["second."]

        accounting.settle.assert_awaited_once_with("costed-run", usage)

    asyncio.run(run())


def test_budget_exhaustion_stops_generation_before_contacting_the_provider():
    async def run():
        provider = Mock(spec=Provider)
        accounting = FakeAccounting(fault=BudgetExhaustedError())
        command = AnswerCommand("costed-run", "Tell me about the API.", "en")

        with pytest.raises(BudgetExhaustedError):
            await anext(generate(command, (SOURCE,), provider, accounting))

        provider.stream.assert_not_called()

    asyncio.run(run())


def test_generation_without_evidence_does_not_reserve_or_settle_usage():
    async def run():
        provider = Mock(spec=Provider)
        provider.stream.return_value = provider_items("No public evidence.", Usage(0, 0))
        accounting = Mock(spec=Accounting, wraps=FakeAccounting())
        command = AnswerCommand("fallback-run", "Tell me about the API.", "en")

        assert [text async for text in generate(command, (), provider, accounting)] == [
            "No public evidence."
        ]
        accounting.reserve.assert_not_awaited()
        accounting.settle.assert_not_awaited()

    asyncio.run(run())


def test_only_text_within_the_cumulative_character_limit_is_yielded():
    async def run():
        provider = Mock(spec=Provider)
        first = "a" * 20_000
        second = "b" * 20_000
        provider.stream.return_value = provider_items(first, second, "!")
        command = AnswerCommand("long-run", "Tell me about the API.", "en")

        async with aclosing(generate(command, (SOURCE,), provider, None)) as stream:
            assert await anext(stream) == first
            assert await anext(stream) == second
            with pytest.raises(GenerationFailedError, match=r"^output_limit$"):
                await anext(stream)

    asyncio.run(run())
