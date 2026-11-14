"""Fault injection over the in-process HTTP/SSE path: documented codes, never a 500."""

import asyncio
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable

from app.adapters.retrieval import KnowledgeIndex
from app.ai.retrieval import PublicRetrieval
from app.application.knowledge import Chunk, Corpus
from app.domain.errors import (
    BudgetExhaustedError,
    DependencyUnavailableError,
    ProviderUnavailableError,
    RejectedError,
)
from tests.support_app import (
    ORIGIN,
    FakeAccounting,
    StubProvider,
    StubRetrieval,
    build_app,
    pin_env,
)

MUTATION = {'Origin': ORIGIN}


class Hang:
    async def stream(self, *args, **kwargs):
        await asyncio.sleep(2)
        yield 'never'


def session(app):
    client = TestClient(app)
    response = client.post(
        '/api/v1/session',
        json={},
        headers={**MUTATION, 'X-Session-Bootstrap': '1'},
    )
    assert response.status_code == 200
    client.headers.update({**MUTATION, 'X-CSRF-Token': response.json()['csrf_token']})
    return client


def stream(client, key='k' * 8):
    conversation = client.post('/api/v1/conversations', json={}).json()
    return client.post(
        f'/api/v1/conversations/{conversation["id"]}/messages/stream',
        json={'content': 'What is Filomena?'},
        headers={'Idempotency-Key': key},
    )


def frames(response):
    return [
        (line[7:], json.loads(data[6:]))
        for block in response.text.split('\n\n')
        if block.startswith('event:')
        for line, data in [block.split('\n', 1)]
    ]


@pytest.mark.parametrize(
    ('app_args', 'code'),
    [
        (
            {'provider': StubProvider(fault=ProviderUnavailableError())},
            'provider_unavailable',
        ),
        ({'provider': StubProvider(fault=RuntimeError('boom'))}, 'generation_failed'),
        pytest.param(
            {'provider': Hang(), 'timeout': 0.3},
            'generation_failed',
            marks=pytest.mark.xfail(
                strict=True,
                reason='RunService asyncio.timeout never fires over HTTP; fixed by PR #178; remove this mark when #178 merges',
            ),
        ),
        (
            {
                'retrieval': StubRetrieval(),
                'accounting': FakeAccounting(BudgetExhaustedError()),
            },
            'budget_exhausted',
        ),
        (
            {'retrieval': StubRetrieval(RejectedError('knowledge_updating', 503))},
            'knowledge_updating',
        ),
    ],
    ids=[
        'provider_error',
        'provider_crash',
        'provider_timeout',
        'budget',
        'knowledge_updating',
    ],
)
def test_run_failures_end_in_documented_terminal_event(app_args, code):
    response = stream(session(build_app(**app_args)))
    assert response.status_code == 200
    names = [name for name, _ in frames(response)]
    assert names[-1] == 'run.failed'
    assert frames(response)[-1][1]['payload'] == {'code': code}
    assert 'message.completed' not in names


def test_run_survives_run_store_outage_with_terminal_event():
    app = build_app()
    client = session(app)
    app.state.run_store.fault = DependencyUnavailableError('storage_unavailable')
    response = stream(client)
    assert response.status_code == 200
    assert frames(response)[-1][0] == 'run.failed'


@pytest.mark.parametrize(
    ('fault', 'status', 'code'),
    [
        (RejectedError('rate_limited', 429), 429, 'rate_limited'),
        (RejectedError('conversation_limit', 429), 429, 'conversation_limit'),
        (
            DependencyUnavailableError('storage_unavailable'),
            503,
            'dependency_unavailable',
        ),
        (RuntimeError('postgres detail'), 503, 'dependency_unavailable'),
    ],
)
def test_storage_faults_return_problem_codes_without_leaking(fault, status, code):
    app = build_app()
    client = session(app)
    app.state.store.fault = fault
    for response in (
        client.get('/api/v1/session'),
        client.post('/api/v1/conversations', json={}),
        client.get('/api/v1/conversations'),
    ):
        assert (response.status_code, response.json()['code']) == (status, code)
        assert 'postgres detail' not in response.text


def test_bootstrap_rate_limit_is_429():
    app = build_app()
    app.state.store.fault = RejectedError('rate_limited', 429)
    response = TestClient(app).post(
        '/api/v1/session', json={}, headers={**MUTATION, 'X-Session-Bootstrap': '1'}
    )
    assert (response.status_code, response.json()['code']) == (429, 'rate_limited')


@pytest.mark.parametrize('path', ['/readyz', '/health/ready'])
def test_readiness_reports_postgres_or_neo4j_down_as_503(path):
    app = build_app()

    def down():
        raise ServiceUnavailable('neo4j password detail')

    app.state.ready = down
    response = TestClient(app).get(path)
    assert (response.status_code, response.json()['code']) == (
        503,
        'dependency_unavailable',
    )
    assert 'password' not in response.text


def test_suggestions_while_knowledge_updating_is_503_code():
    app = build_app()

    def updating(locale):
        raise RejectedError('knowledge_updating', 503)

    app.state.knowledge.starter_prompts = updating
    response = TestClient(app).get('/api/v1/knowledge/suggestions')
    assert (response.status_code, response.json()['code']) == (
        503,
        'knowledge_updating',
    )


PATHS = {'alpha': 'src/content/en/projects.ts', 'beta': 'src/content/en/profile.ts'}


def chunk(name, text):
    path, sha = PATHS[name], 'a' * 40
    url = f'https://github.com/gonzalomartinperez/portfolio/blob/{sha}/{path}#L1-L2'
    digest = hashlib.sha256(text.encode()).hexdigest()
    return Chunk(name, name, url, 'code', path, 1, 2, text, digest)


class Broken:
    """Neo4j driver whose every session is unavailable."""

    def session(self, **kwargs):
        raise ServiceUnavailable('neo4j down')


class Postgres:
    async def candidates(self, question):
        chunks = tuple(chunk(n, f'name: "{n}" python rust') for n in ('alpha', 'beta'))
        return Corpus(
            'v',
            'a' * 40,
            chunks,
            frozenset(c.path for c in chunks),
            ('beta',),
            ('alpha',),
        )

    async def relationships(self, version, terms, locale='en', expand=False):
        return await KnowledgeIndex(None, Broken()).relationships(
            version, terms, locale, expand
        )


def test_graph_failure_degrades_to_vector_and_lexical():
    found = asyncio.run(
        PublicRetrieval(Postgres()).search('compare alpha and beta python', 'en')
    )
    assert {source.id for source in found} == {'alpha', 'beta'}


@pytest.fixture(autouse=True)
def hermetic(monkeypatch):
    pin_env(monkeypatch)


def test_midstream_provider_failure_after_first_delta_ends_in_run_failed():
    class Partial:
        async def stream(self, *args, **kwargs):
            yield 'first '
            raise ProviderUnavailableError

    names = [n for n, _ in frames(stream(session(build_app(provider=Partial()))))]
    assert names[-1] == 'run.failed'
    assert 'message.delta' in names
    assert 'message.completed' not in names


def test_real_translated_adapter_maps_psycopg_outage_to_dependency_unavailable():
    from contextlib import contextmanager

    import psycopg

    from app.adapters.postgres.conversations import PostgresConversations
    from app.adapters.postgres.db import translated

    @contextmanager
    def down():
        raise psycopg.OperationalError('connection refused: postgres://secret')
        yield

    client = TestClient(build_app(store=PostgresConversations(translated(down))))
    response = client.post(
        '/api/v1/session',
        json={},
        headers={**MUTATION, 'X-Session-Bootstrap': '1'},
    )
    assert (response.status_code, response.json()['code']) == (
        503,
        'dependency_unavailable',
    )
    assert 'secret' not in response.text
