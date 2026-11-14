"""Run scripted items through the real session, conversation and SSE endpoints.

The provider is injected and required: any object satisfying
``app.application.contracts.Provider`` (the fixture provider or a test double today; the
cassette replayer of M2-7 plugs into the same port). The wire exposes no abstention
flag, so ``abstained`` means a completed run with no citations and the ``abstains``
grader adds a text cue check. ``first_delta_ms`` is measured inside ``RecordingProvider``
at the first yielded text, because the ASGI transport buffers the response body; it is
therefore relative to the turn start but excludes transport delivery.
"""

import json
import re
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing
from dataclasses import replace
from uuid import uuid4

import httpx

from app.application.contracts import Provider, Usage
from app.application.conversation_context import Turn
from app.application.presentation_context import PresentationContext
from app.bootstrap.config import Settings
from app.bootstrap.container import create_app
from app.domain.portfolio_paths import canonical_key
from evals.harness.graders import grade_item
from evals.harness.isolation import require_isolated
from evals.harness.items import Item
from evals.harness.report import ItemOutcome
from evals.harness.result import CitedSource, GradingContext, RunResult
from scripts.evaluation_isolation import EvaluationContainer, inspect_containers

_CANONICAL_URL = re.compile(r'canonical_url=(\S+?):?(?=\s|$)')
_SOURCE = re.compile(r'^PUBLIC SOURCE \[\d+\] (\S+) lines \d+-\d+', re.MULTILINE)


class RecordingProvider:
    """Wrap a provider and record the evidence it was given, usage and call count."""

    def __init__(self, inner: Provider) -> None:
        self.inner = inner
        self.evidence: list[str] = []
        self.usage: list[Usage] = []
        self.first_text_at: list[float | None] = []  # parallel to ``evidence``

    async def stream(
        self,
        question: str,
        evidence: str,
        locale: str,
        history: tuple[Turn, ...] = (),
        context: PresentationContext | None = None,
    ) -> AsyncGenerator[str | Usage]:
        self.evidence.append(evidence)
        self.first_text_at.append(None)
        call = len(self.first_text_at) - 1
        async with aclosing(
            self.inner.stream(question, evidence, locale, history, context)
        ) as stream:
            async for item in stream:
                if isinstance(item, Usage):
                    self.usage.append(item)
                elif self.first_text_at[call] is None:
                    self.first_text_at[call] = time.perf_counter()
                yield item


def parse_sse(text: str) -> list[tuple[str, dict[str, object]]]:
    """Return ``(event name, data)`` pairs, ignoring comments such as keep-alives."""
    events = []
    for frame in text.split('\n\n'):
        name = ''
        data = ''
        for line in frame.splitlines():
            if line.startswith('event: '):
                name = line[7:]
            elif line.startswith('data: '):
                data = line[6:]
        if name and data:
            events.append((name, json.loads(data)))
    return events


def collect(
    events: list[tuple[str, dict[str, object]]],
    *,
    question: str,
    evidence: list[str],
    usage: list[Usage],
    first_delta_ms: float | None,
    total_ms: float,
) -> RunResult:
    """Pure fold of one turn's events and provider observations into a ``RunResult``."""
    names = tuple(name for name, _ in events)
    message = next((d['payload'] for n, d in events if n == 'message.completed'), None)
    payload = message if isinstance(message, dict) else {}
    citations = tuple(
        CitedSource(canonical_key(c.get('path') or c['url']), c['url'])
        for c in payload.get('citations', [])
    )
    terminal = next(
        (n for n in names if n in ('run.completed', 'run.failed', 'run.cancelled')),
        None,
    )
    text = '\n'.join(evidence)
    return RunResult(
        answer=str(payload.get('content', '')),
        events=names,
        citations=citations,
        retrieved_keys=tuple(canonical_key(path) for path in _SOURCE.findall(text))
        if evidence
        else None,
        evidence_text=text if evidence else None,
        question=question,
        abstained=terminal == 'run.completed' and not citations,
        input_tokens=sum(u.input_tokens for u in usage) if usage else None,
        output_tokens=sum(u.output_tokens for u in usage) if usage else None,
        llm_calls=len(evidence),
        first_delta_ms=first_delta_ms,
        total_ms=total_ms,
        terminal=terminal,
    )


def item_context(
    item: Item, result: RunResult, base: GradingContext | None = None
) -> GradingContext:
    """Extend the grading context with this item's approved URLs.

    ``tools.host_allowed`` (a host string or a list of hosts) approves ``https://<host>``
    and its paths; canonical source URLs the provider was shown are approved exactly.
    """
    base = base or GradingContext()
    hosts = (item.tools or {}).get('host_allowed')
    names = (
        [hosts] if isinstance(hosts, str) else hosts if isinstance(hosts, list) else []
    )
    approved = {f'https://{h}' for h in names if isinstance(h, str) and h}
    approved |= set(_CANONICAL_URL.findall(result.evidence_text or ''))
    return replace(base, approved_urls=base.approved_urls | frozenset(approved))


async def run_item(
    item: Item,
    client: httpx.AsyncClient,
    recorder: RecordingProvider,
    *,
    origin: str,
    visitor: str,
) -> RunResult:
    """Replay the item's user turns in one conversation; the result is the last turn."""
    forwarded = {'X-Forwarded-For': visitor, 'Origin': origin}
    session = await client.post(
        '/api/v1/session', headers={**forwarded, 'X-Session-Bootstrap': '1'}, json={}
    )
    session.raise_for_status()
    headers = {**forwarded, 'X-CSRF-Token': session.json()['csrf_token']}
    try:
        created = await client.post('/api/v1/conversations', headers=headers, json={})
        created.raise_for_status()
        path = f'/api/v1/conversations/{created.json()["id"]}/messages/stream'
        result = RunResult(answer='')
        for turn in item.turns:
            mark = (len(recorder.evidence), len(recorder.usage))
            started = time.perf_counter()
            body = ''
            async with client.stream(
                'POST',
                path,
                headers={**headers, 'Idempotency-Key': str(uuid4())},
                json={'content': turn.text, 'locale': item.locale},
            ) as stream:
                stream.raise_for_status()
                async for chunk in stream.aiter_text():
                    body += chunk
            stamps = [t for t in recorder.first_text_at[mark[0] :] if t is not None]
            first = round((stamps[0] - started) * 1000, 2) if stamps else None
            result = collect(
                parse_sse(body),
                question=turn.text,
                evidence=recorder.evidence[mark[0] :],
                usage=recorder.usage[mark[1] :],
                first_delta_ms=first,
                total_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        return result
    finally:
        await client.delete('/api/v1/session', headers=headers)


async def run_items(
    items: list[Item],
    config: Settings,
    provider: Provider,
    *,
    ctx: GradingContext | None = None,
    inspect: Callable[
        [tuple[str, str]], list[EvaluationContainer]
    ] = inspect_containers,
) -> list[ItemOutcome]:
    """Grade items against the in-process app; refuses unless the isolation guard passes.

    Retired items are skipped; quarantined items run and are reported separately.
    """
    require_isolated(config, inspect=inspect)
    # Synthetic loopback visitors: trust the forwarded address so per-subject limits apply.
    config = config.model_copy(update={'trusted_proxy_ips': '127.0.0.1'})
    recorder = RecordingProvider(provider)
    app = create_app(config, provider_override=recorder)
    outcomes = []
    runnable = [item for item in items if item.status != 'retired']
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, client=('127.0.0.1', 50000))
        async with httpx.AsyncClient(
            transport=transport, base_url='http://eval.local', timeout=130
        ) as client:
            for index, item in enumerate(runnable):
                result = await run_item(
                    item,
                    client,
                    recorder,
                    origin=config.origins[0],
                    visitor=f'198.18.{index // 250}.{index % 250 + 1}',
                )
                outcomes.append(
                    ItemOutcome(
                        item.id,
                        item.locale,
                        tuple(item.strata),
                        grade_item(item, result, item_context(item, result, ctx)),
                        item.status,
                    )
                )
    return outcomes
