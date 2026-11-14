"""Runner pipeline: SSE parsing, result collection, grading and the isolation refusal.

The app needs PostgreSQL and Neo4j, so the real in-process run is an integration test;
the offline tests drive ``run_item`` against a fake of the documented endpoints.
"""

import asyncio
import json
import os
import time
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest

from app.application.contracts import Usage
from app.bootstrap.config import Settings
from evals.harness.graders.citations import citation_urls_allowlisted
from evals.harness.isolation import IsolationError
from evals.harness.items import Item
from evals.harness.result import GradingContext, RunResult
from evals.harness.runner import (
    RecordingProvider,
    collect,
    item_context,
    parse_sse,
    run_item,
    run_items,
)
from tests.evals.support import PINNED, make_item

EVIDENCE = (
    'PUBLIC SOURCE [1] src/content/en/education.ts lines 1-5:\nUniversidad Nacional del Sur\n'
    'PUBLIC SOURCE [2] content/en/profile.ts lines 3-9:\nProfile'
)


def frame(name: str, payload: dict) -> str:
    data = {'type': name, 'payload': payload}
    return f'event: {name}\ndata: {json.dumps(data)}\n\n'


def stream_body(
    answer: str, citations: list[dict], terminal: str = 'run.completed'
) -> str:
    return (
        ': keep-alive\n\n'
        + frame('run.started', {})
        + frame('run.status', {'phase': 'evidence_found', 'sources': 2})
        + frame('message.delta', {'text': answer[:5]})
        + frame(
            'message.completed',
            {'message_id': 'm', 'content': answer, 'citations': citations},
        )
        + frame(terminal, {'state': 'completed'})
    )


CITATION = {
    'id': 'c1',
    'label': 'Education',
    'url': PINNED,
    'source_type': 'code',
    'path': 'src/content/en/education.ts',
}


def test_parse_sse_ignores_comments_and_partial_frames():
    body = stream_body('Hello', [])
    parsed = parse_sse(body + 'event: dangling\n\n')
    assert [name for name, _ in parsed] == [
        'run.started',
        'run.status',
        'message.delta',
        'message.completed',
        'run.completed',
    ]


def test_collect_folds_events_and_provider_observations():
    events = parse_sse(stream_body('He studied at UNS [1].', [CITATION]))
    result = collect(
        events,
        question='Where?',
        evidence=[EVIDENCE],
        usage=[Usage(100, 20), Usage(5, 1)],
        first_delta_ms=12.0,
        total_ms=80.0,
    )
    assert result.answer == 'He studied at UNS [1].'
    assert result.events[0] == 'run.started'
    assert result.terminal == 'run.completed'
    assert [c.key for c in result.citations] == ['en/education']
    assert result.retrieved_keys == ('en/education', 'en/profile')
    assert (result.input_tokens, result.output_tokens, result.llm_calls) == (105, 21, 1)
    assert not result.abstained


def test_collect_without_provider_observation_or_message():
    result = collect(
        parse_sse(frame('run.started', {}) + frame('run.failed', {'code': 'x'})),
        question='q',
        evidence=[],
        usage=[],
        first_delta_ms=None,
        total_ms=1.0,
    )
    assert result.answer == ''
    assert result.terminal == 'run.failed'
    assert result.retrieved_keys is None and result.evidence_text is None
    assert result.input_tokens is None
    assert not result.abstained


def test_collect_marks_completed_run_without_citations_as_abstention():
    events = parse_sse(stream_body('Not in the portfolio.', []))
    result = collect(
        events,
        question='q',
        evidence=[EVIDENCE],
        usage=[],
        first_delta_ms=1.0,
        total_ms=2.0,
    )
    assert result.abstained


def fake_app(
    recorder: RecordingProvider, answers: list[str], calls: list[tuple[str, str]]
):
    state = {'turn': 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == '/api/v1/session':
            if request.method == 'DELETE':
                return httpx.Response(204)
            assert request.headers['X-Session-Bootstrap'] == '1'
            return httpx.Response(200, json={'csrf_token': 'token'})
        assert request.headers['X-CSRF-Token'] == 'token'
        if request.url.path == '/api/v1/conversations':
            return httpx.Response(201, json={'id': str(uuid4())})
        recorder.evidence.append(EVIDENCE)
        recorder.first_text_at.append(time.perf_counter())
        recorder.usage.append(Usage(10, 2))
        answer = answers[state['turn']]
        state['turn'] += 1
        assert json.loads(request.content)['content']
        return httpx.Response(200, content=stream_body(answer, [CITATION]).encode())

    return handler


def test_run_item_replays_every_turn_and_returns_the_last():
    item: Item = make_item(
        turns=[{'text': 'Where did he study?'}, {'text': 'Shorten it'}],
        assertions=['citations_in_retrieved', 'budget_respected', 'citations_nonempty'],
    )
    recorder = RecordingProvider(None)  # type: ignore[arg-type]
    calls: list[tuple[str, str]] = []

    async def go():
        transport = httpx.MockTransport(
            fake_app(recorder, ['First [1].', 'Second [1].'], calls)
        )
        async with httpx.AsyncClient(
            transport=transport, base_url='http://x'
        ) as client:
            return await run_item(
                item, client, recorder, origin='http://o', visitor='198.18.0.1'
            )

    result = asyncio.run(go())
    assert result.answer == 'Second [1].'
    assert result.llm_calls == 1  # per-turn slice, not cumulative
    assert result.first_delta_ms is not None and result.total_ms is not None
    assert [path for _, path in calls].count('/api/v1/conversations') == 1
    assert calls[-1] == ('DELETE', '/api/v1/session')


def test_session_is_deleted_when_a_turn_fails():
    recorder = RecordingProvider(None)  # type: ignore[arg-type]
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == '/api/v1/session' and request.method == 'POST':
            return httpx.Response(200, json={'csrf_token': 't'})
        if request.url.path == '/api/v1/conversations':
            return httpx.Response(500)
        return httpx.Response(204)

    async def go():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url='http://x'
        ) as client:
            await run_item(
                make_item(), client, recorder, origin='http://o', visitor='198.18.0.1'
            )

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(go())
    assert calls[-1] == ('DELETE', '/api/v1/session')


def test_first_delta_is_taken_from_the_provider_not_the_buffered_body():
    class Slow:
        async def stream(self, question, evidence, locale, history=(), context=None):
            await asyncio.sleep(0.05)
            yield 'a'
            await asyncio.sleep(0.2)
            yield 'b'

    recorder = RecordingProvider(Slow())
    stamps = []

    async def go():
        started = time.perf_counter()
        async for _ in recorder.stream('q', 'ev', 'en'):
            stamps.append(time.perf_counter() - started)
        return recorder.first_text_at[0] - started

    first = asyncio.run(go())
    assert 0.04 < first < 0.15  # well before the end of the stream
    assert stamps[-1] > first + 0.15


def test_item_context_approves_allowlisted_hosts_and_canonical_urls():
    evidence = f'PUBLIC SOURCE [1] content/en/profile.ts lines 1-5 canonical_url={PINNED}:\nText'
    result = RunResult(
        answer='See https://docs.python.org/3/library/ and https://evil.example/x and '
        f'{PINNED}.',
        evidence_text=evidence,
    )
    plain = make_item()
    hosted = make_item(tools={'host_allowed': ['docs.python.org']})
    assert not citation_urls_allowlisted(
        plain, result, item_context(plain, result)
    ).passed
    only_docs = replace(result, answer='See https://docs.python.org/3/library/.')
    assert citation_urls_allowlisted(
        hosted, only_docs, item_context(hosted, only_docs)
    ).passed
    assert not citation_urls_allowlisted(
        plain, only_docs, item_context(plain, only_docs)
    ).passed
    assert not citation_urls_allowlisted(
        hosted, result, item_context(hosted, result)
    ).passed  # evil.example stays rejected
    canonical = replace(result, answer=f'Source: {PINNED}.')
    assert citation_urls_allowlisted(
        plain, canonical, item_context(plain, canonical)
    ).passed
    single = make_item(tools={'host_allowed': 'docs.python.org'})
    assert citation_urls_allowlisted(
        single, only_docs, item_context(single, only_docs)
    ).passed
    flag = make_item(tools={'host_allowed': True})
    assert item_context(flag, only_docs).approved_urls == frozenset({PINNED})
    base = GradingContext(approved_urls=frozenset({'https://x.example'}))
    assert 'https://x.example' in item_context(plain, only_docs, base).approved_urls


def test_recording_provider_passes_text_and_usage_through():
    class Inner:
        async def stream(self, question, evidence, locale, history=(), context=None):
            yield 'a'
            yield 'b'
            yield Usage(3, 4)

    recorder = RecordingProvider(Inner())

    async def go():
        return [x async for x in recorder.stream('q', 'ev', 'en')]

    assert asyncio.run(go())[:2] == ['a', 'b']
    assert recorder.evidence == ['ev']
    assert recorder.usage == [Usage(3, 4)]


def test_run_items_refuses_remote_targets_before_building_the_app():
    config = Settings(
        _env_file=None,
        ai_provider='fixture',
        embeddings_provider='fixture',
        database_url='postgresql://u@db.example.com/db',
    )
    with pytest.raises(IsolationError):
        asyncio.run(run_items([make_item()], config, provider=None))  # type: ignore[arg-type]


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv('TEST_INTEGRATION') != '1', reason='isolated stores required'
)
def test_real_app_run_through_the_sse_path():
    from app.bootstrap.config import settings

    class Provider:
        async def stream(self, question, evidence, locale, history=(), context=None):
            yield 'Gonzalo studied at the Universidad Nacional del Sur [1].'
            yield Usage(10, 10)

    item = make_item(
        assertions=['required_facts_present', 'citations_nonempty'],
        required_facts=[{'id': 'uns', 'match': 'Universidad Nacional del Sur'}],
    )
    outcomes = asyncio.run(
        run_items([item], settings(), Provider(), ctx=GradingContext())
    )
    assert outcomes[0].passed
