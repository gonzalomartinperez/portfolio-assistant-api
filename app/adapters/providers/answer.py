"""Translate existing retrieval/accounting and vendor events into inner contracts."""

import asyncio
import json
from collections.abc import AsyncGenerator, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime

from openai import APIError

from app.adapters.providers.voice import developer_prompt
from app.application.contracts import GenerationFailedError, Usage
from app.application.conversation_context import (
    Turn,
    bounded_history,
    retrieval_question,
)
from app.application.presentation_context import PresentationContext
from app.application.web_context import WebSearch, WebSupplement, supplement
from app.domain.budget import MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS
from app.domain.errors import ProviderUnavailableError
from app.domain.fixture import fixture_message
from app.domain.privacy import minimize_visitor_text

REASONING_EFFORT = 'medium'


@dataclass(frozen=True)
class ModelRequest:
    """The exact messages sent to the model and the prompt_version that produced them."""

    messages: list[dict[str, str]]
    prompt_version: str


def visitor_inputs(
    question: str, history: tuple[Turn, ...]
) -> tuple[str, tuple[Turn, ...]]:
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
        {'role': 'developer', 'content': developer},
        {
            'role': 'user',
            'content': json.dumps(
                {
                    'public_evidence': evidence,
                    'untrusted_external_technical_context': asdict(web)
                    if web
                    else None,
                    'untrusted_conversation': [asdict(turn) for turn in history],
                    'untrusted_presentation_context': asdict(context)
                    if context
                    else None,
                    'question': question,
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
        answer = fixture_message(
            retrieval_question(question, history), evidence, locale
        )
        for offset in range(0, len(answer), 48):
            yield answer[offset : offset + 48]
            await asyncio.sleep(0)


class ResponsesProvider:
    def __init__(
        self,
        client,
        model: str,
        rejects_language: Callable[[str], bool] | None = None,
        web_search: WebSearch | None = None,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ):
        self.today = today
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
        if not evidence:
            yield fixture_message(question, evidence, locale)
            return
        question, history = visitor_inputs(question, history)
        web = await supplement(question, evidence, self.web_search)
        request = assemble_request(
            question, evidence, locale, history, context, web, self.today()
        )
        messages, prompt_version = request.messages, request.prompt_version
        # Bound the escaped text actually sent, with room for message framing.
        input_bytes = sum(
            len(message['content'].encode('utf-8')) for message in messages
        )
        if input_bytes + 1024 > MAX_INPUT_TOKENS:
            raise GenerationFailedError('input_limit')
        try:
            events = await self.client.responses.create(
                model=self.model,
                input=messages,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                reasoning={'effort': REASONING_EFFORT},
                store=False,
                stream=True,
            )
        except APIError:
            raise ProviderUnavailableError('provider_unavailable') from None
        completed = False
        prefix = ''
        language_checked = self.rejects_language is None
        try:
            async for event in events:
                if event.type == 'response.output_text.delta' and event.delta:
                    if language_checked:
                        yield event.delta
                    else:
                        prefix += event.delta
                        if len(prefix) >= 256:
                            if self.rejects_language and self.rejects_language(
                                prefix[:512]
                            ):
                                raise GenerationFailedError('output_language')
                            language_checked = True
                            yield prefix
                            prefix = ''
                elif event.type == 'response.completed':
                    if prefix:
                        if self.rejects_language and self.rejects_language(prefix):
                            raise GenerationFailedError('output_language')
                        yield prefix
                        prefix = ''
                    completed = True
                    usage = event.response.usage
                    if usage is not None:
                        yield Usage(
                            usage.input_tokens,
                            usage.output_tokens,
                            prompt_version,
                        )
                elif event.type in ('response.failed', 'response.incomplete', 'error'):
                    raise GenerationFailedError('provider_failed')
            if not completed:
                raise GenerationFailedError('provider_interrupted')
        except APIError:
            raise ProviderUnavailableError('provider_unavailable') from None
        finally:
            await events.close()
