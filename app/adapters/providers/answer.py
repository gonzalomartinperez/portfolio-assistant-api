"""Translate existing retrieval/accounting and vendor events into inner contracts."""

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Final, cast

from openai import APIError, AsyncOpenAI

from app.adapters.providers.fixture_answer import fixture_message
from app.adapters.providers.voice import developer_prompt
from app.application.contracts import GenerationFailedError, Usage
from app.application.conversation_context import (
    Turn,
    bounded_history,
    retrieval_question,
)
from app.application.web_context import WebSearch, WebSupplement, supplement
from app.domain.budget import MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS
from app.domain.errors import ProviderUnavailableError
from app.domain.privacy import minimize_visitor_text

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Callable
    from datetime import date

    from openai import AsyncStream
    from openai.types.responses import ResponseInputParam, ResponseStreamEvent

    from app.application.clock import Clock
    from app.application.presentation_context import PresentationContext

REASONING_EFFORT: Final = "medium"


@dataclass(frozen=True)
class ModelRequest:
    """The exact messages sent to the model and the prompt_version that produced them."""

    messages: list[dict[str, str]]
    prompt_version: str


def visitor_inputs(question: str, history: tuple[Turn, ...]) -> tuple[str, tuple[Turn, ...]]:
    """Minimize the visitor question and bound the history before they reach a prompt."""
    return minimize_visitor_text(question), bounded_history(history)


def assemble_request(
    question: str,
    evidence: str,
    locale: str,
    history: tuple[Turn, ...],
    context: PresentationContext | None,
    web: WebSupplement | None,
    today: date,
) -> ModelRequest:
    """Pure assembly of the model messages; inputs are already from ``visitor_inputs``.

    Shared by the real provider and the eval cassette key, so a recorded key always
    describes the request the provider would send.
    """
    developer, prompt_version = developer_prompt(locale, bool(web), today)
    messages = [
        {"role": "developer", "content": developer},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "public_evidence": evidence,
                    "untrusted_external_technical_context": asdict(web) if web else None,
                    "untrusted_conversation": [asdict(turn) for turn in history],
                    "untrusted_presentation_context": asdict(context) if context else None,
                    "question": question,
                },
                ensure_ascii=False,
            ),
        },
    ]
    return ModelRequest(messages, prompt_version)


class FixtureProvider:
    async def stream(
        self,
        question: str,
        evidence: str,
        locale: str,
        history: tuple[Turn, ...] = (),
        context: PresentationContext | None = None,
    ) -> AsyncGenerator[str | Usage]:
        answer = fixture_message(retrieval_question(question, history), evidence, locale)
        for offset in range(0, len(answer), 48):
            yield answer[offset : offset + 48]
            await asyncio.sleep(0)


class ResponsesProvider:
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        rejects_language: Callable[[str], bool] | None = None,
        web_search: WebSearch | None = None,
        today: Callable[[], date] | None = None,
        *,
        clock: Clock,
    ):
        self.today = today if today is not None else (lambda: clock.now().date())
        self.client = client
        self.model = model
        self.rejects_language = rejects_language
        self.web_search = web_search

    async def stream(
        self,
        question: str,
        evidence: str,
        locale: str,
        history: tuple[Turn, ...] = (),
        context: PresentationContext | None = None,
    ) -> AsyncGenerator[str | Usage]:
        """Stream translated deltas and usage with the SDK stream scoped to this call."""
        if not evidence:
            yield fixture_message(question, evidence, locale)
            return
        question, history = visitor_inputs(question, history)
        web = await supplement(question, evidence, self.web_search)
        request = assemble_request(question, evidence, locale, history, context, web, self.today())
        messages, prompt_version = request.messages, request.prompt_version
        async with self._open_events(messages) as events:
            completed = False
            prefix = "" if self.rejects_language is not None else None
            async for event in events:
                if event.type == "response.output_text.delta" and event.delta:
                    prefix, text = self._accept_delta(prefix, event.delta)
                    if text:
                        yield text
                elif event.type == "response.completed":
                    if prefix:
                        self._check_language(prefix)
                        yield prefix
                        prefix = ""
                    completed = True
                    usage = event.response.usage
                    if usage is not None:
                        yield Usage(
                            usage.input_tokens,
                            usage.output_tokens,
                            prompt_version,
                        )
                elif event.type in ("response.failed", "response.incomplete", "error"):
                    raise GenerationFailedError("provider_failed")
            if not completed:
                raise GenerationFailedError("provider_interrupted")

    @asynccontextmanager
    async def _open_events(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[AsyncStream[ResponseStreamEvent]]:
        """Enforce the request bound and close the SDK stream on every exit."""
        # Bound the escaped text actually sent, with room for message framing.
        input_bytes = sum(len(message["content"].encode("utf-8")) for message in messages)
        if input_bytes + 1024 > MAX_INPUT_TOKENS:
            raise GenerationFailedError("input_limit")
        try:
            events = await self.client.responses.create(
                model=self.model,
                input=cast("ResponseInputParam", messages),
                max_output_tokens=MAX_OUTPUT_TOKENS,
                reasoning={"effort": REASONING_EFFORT},
                store=False,
                stream=True,
            )
        except APIError:
            raise ProviderUnavailableError("provider_unavailable") from None
        try:
            yield events
        except APIError:
            raise ProviderUnavailableError("provider_unavailable") from None
        finally:
            await events.close()

    def _accept_delta(self, prefix: str | None, delta: str) -> tuple[str | None, str]:
        """Buffer the initial text while a language check is pending."""
        if prefix is None:
            return None, delta
        prefix += delta
        if len(prefix) < 256:
            return prefix, ""
        self._check_language(prefix[:512])
        return None, prefix

    def _check_language(self, text: str) -> None:
        """Reject disallowed output before exposing the buffered text."""
        if self.rejects_language and self.rejects_language(text):
            raise GenerationFailedError("output_language")
