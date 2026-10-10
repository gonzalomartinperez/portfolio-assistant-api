import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from neo4j import GraphDatabase

from app.bootstrap.config import settings
from app.infrastructure.db import connect
from app.infrastructure.embedding import embed
from app.infrastructure.ledger import BudgetExhaustedError, reserve, settle
from app.main import app
from app.migrate import main as migrate
from tests.support import retrieve

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv('TEST_INTEGRATION') != '1',
        reason='requires real PostgreSQL and Neo4j',
    ),
]


def headers(origin: str, csrf: str) -> dict:
    return {'Origin': origin, 'X-CSRF-Token': csrf}


def bootstrap(client: TestClient, origin: str):
    response = client.post(
        '/api/v1/session',
        headers={'Origin': origin, 'X-Session-Bootstrap': '1'},
        json={},
    )
    assert response.status_code == 200
    return response.json()['csrf_token']


def test_same_origin_embed_contract_needs_no_parent_api_permission(client_factory):
    from app.bootstrap.config import Settings
    from app.bootstrap.container import create_app

    origin = 'https://assistant.gonzalomartinperez.com'
    parent = 'https://gonzalomartinperez.com'
    application = create_app(Settings(allowed_origins=origin, secure_cookies=True))
    client = client_factory(application, base_url=origin, client=(str(uuid4()), 50000))
    response = client.post(
        '/api/v1/session',
        headers={'Origin': origin, 'X-Session-Bootstrap': '1'},
        json={},
    )
    assert response.status_code == 200
    cookie = response.headers['set-cookie']
    assert cookie.startswith('__Host-assistant_session=')
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    assert 'Domain=' not in cookie and 'Path=/' in cookie
    csrf = response.json()['csrf_token']
    assert (
        client.post(
            '/api/v1/conversations', headers={'Origin': origin}, json={}
        ).status_code
        == 403
    )
    assert (
        client.post(
            '/api/v1/conversations', headers=headers(parent, csrf), json={}
        ).status_code
        == 403
    )
    preflight = client.options(
        '/api/v1/conversations',
        headers={'Origin': parent, 'Access-Control-Request-Method': 'POST'},
    )
    assert 'access-control-allow-origin' not in preflight.headers
    created = client.post(
        '/api/v1/conversations', headers=headers(origin, csrf), json={}
    )
    assert created.status_code == 200
    assert (
        client.get(f'/api/v1/conversations/{created.json()["id"]}/messages').status_code
        == 200
    )
    assert (
        client.delete('/api/v1/session', headers=headers(origin, csrf)).status_code
        == 204
    )


def test_sessions_stream_idempotency_and_ownership(client_factory):
    migrate()
    first = client_factory(app, client=(str(uuid4()), 50000))
    second = client_factory(app, client=(str(uuid4()), 50000))
    a = bootstrap(first, 'http://localhost:3000')
    b = bootstrap(second, 'http://localhost:3001')
    conv = first.post(
        '/api/v1/conversations', headers=headers('http://localhost:3000', a), json={}
    )
    assert conv.status_code == 200
    cid = conv.json()['id']
    assert second.get(f'/api/v1/conversations/{cid}/messages').status_code == 404
    assert (
        first.patch(
            f'/api/v1/conversations/{cid}',
            headers={'Origin': 'http://localhost:3000'},
            json={'title': 'x'},
        ).status_code
        == 403
    )
    key = str(uuid4())
    payload = {'content': 'What is Filomena?', 'locale': 'en'}
    sent = first.post(
        f'/api/v1/conversations/{cid}/messages/stream',
        headers={**headers('http://localhost:3000', a), 'Idempotency-Key': key},
        json=payload,
    )
    assert sent.status_code == 200
    assert 'event: run.completed' in sent.text
    assert 'event: message.completed' in sent.text
    duplicate = first.post(
        f'/api/v1/conversations/{cid}/messages/stream',
        headers={**headers('http://localhost:3000', a), 'Idempotency-Key': key},
        json=payload,
    )
    assert duplicate.status_code == 409
    assert second.get(f'/api/v1/runs/{sent.headers["x-run-id"]}').status_code == 404
    allowed_preflight = first.options(
        '/api/v1/conversations',
        headers={
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'x-csrf-token,content-type',
        },
    )
    assert (
        allowed_preflight.headers['access-control-allow-origin']
        == 'http://localhost:3000'
    )
    assert 'Origin' in allowed_preflight.headers['vary']
    denied_preflight = first.options(
        '/api/v1/conversations',
        headers={
            'Origin': 'https://evil.example',
            'Access-Control-Request-Method': 'POST',
        },
    )
    assert 'access-control-allow-origin' not in denied_preflight.headers
    reserve(sent.headers['x-run-id'], Decimal('0.05'))
    settle(sent.headers['x-run-id'], 1000, 500)
    with pytest.raises(BudgetExhaustedError):
        reserve(str(uuid4()), Decimal('10.01'))
    pending_id = str(uuid4())
    with connect() as conn:
        conn.execute(
            "INSERT INTO runs(id,conversation_id,idempotency_key,payload_hash,state,lease_until) VALUES (%s,%s,%s,%s,'pending',now()-interval '1 minute')",
            (
                pending_id,
                cid,
                str(uuid4()),
                'test',
            ),
        )
    assert first.get(f'/api/v1/runs/{pending_id}').json()['state'] == 'interrupted'
    cancellable_id = str(uuid4())
    with connect() as conn:
        conn.execute(
            "INSERT INTO runs(id,conversation_id,idempotency_key,payload_hash,state,lease_until) VALUES (%s,%s,%s,%s,'pending',now()+interval '5 minutes')",
            (cancellable_id, cid, str(uuid4()), 'test'),
        )
    assert (
        first.post(
            f'/api/v1/runs/{cancellable_id}/cancel',
            headers=headers('http://localhost:3000', a),
        ).json()['state']
        == 'cancelled'
    )
    saved = first.get(f'/api/v1/conversations/{cid}/messages').json()['items']
    assert len(saved) == 2
    assert saved[0]['citations'][0]['url'].startswith(
        'https://github.com/gonzalomartinperez/portfolio/blob/'
    )
    unsupported = first.post(
        f'/api/v1/conversations/{cid}/messages/stream',
        headers={
            **headers('http://localhost:3000', a),
            'Idempotency-Key': str(uuid4()),
        },
        json={'content': 'quasar xylophone', 'locale': 'en'},
    )
    assert unsupported.status_code == 200
    assert 'not find enough public evidence' in unsupported.text
    assert '"citations":[]' in unsupported.text
    assert (
        first.delete(
            '/api/v1/session', headers=headers('http://localhost:3000', a)
        ).status_code
        == 204
    )
    assert first.get(f'/api/v1/conversations/{cid}/messages').status_code == 401
    second.delete('/api/v1/session', headers=headers('http://localhost:3001', b))


def test_real_vector_and_graph():
    with connect() as conn:
        count = conn.execute(
            "SELECT count(*) AS n FROM chunks c JOIN knowledge_versions v ON v.id=c.knowledge_version WHERE v.status='active' AND c.embedding <=> %s::vector IS NOT NULL",
            (embed('Filomena'),),
        ).fetchone()['n']
    assert count > 0
    rows, commits = retrieve('What is Filomena?')
    assert len(rows) > 0 and len(commits[0]) == 40
    unsupported, _ = retrieve('quasar xylophone')
    assert unsupported == []
    driver = GraphDatabase.driver(
        settings().neo4j_uri, auth=(settings().neo4j_user, settings().neo4j_password)
    )
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (:Entity {name:$name,kind:'Project'})-[:SUPPORTED_BY]->(d:Document) RETURN count(d) AS n",
                name='Filomena',
            ).single()
            assert result['n'] > 0
    finally:
        driver.close()


def test_incremental_sync_and_failed_projection_keep_previous_version(
    tmp_path, monkeypatch
):
    import subprocess

    from app.knowledge_sync import sync

    repo = tmp_path / 'portfolio'
    repo.mkdir()

    def command(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args]).decode().strip()

    command('init', '-q')
    command('config', 'user.name', 'Fixture Test')
    command('config', 'user.email', 'fixture@example.invalid')
    command(
        'remote', 'add', 'origin', 'https://github.com/gonzalomartinperez/portfolio.git'
    )
    (repo / 'docs').mkdir()
    (repo / 'README.md').write_text(
        '# Public fixture\nThis is a public fixture document used only for integration tests.\n'
    )
    (repo / 'docs' / 'development.md').write_text(
        '# Development\nThe fixture verifies bounded incremental sync behavior in real databases.\n'
    )
    command('add', '.')
    command('commit', '-qm', 'fixture: initial')
    with connect() as conn:
        original = conn.execute(
            "SELECT id FROM knowledge_versions WHERE status='active'"
        ).fetchone()['id']
    try:
        first = sync(repo)
        assert first['embedded_chunks'] == first['chunks']
        (repo / 'README.md').write_text(
            '# Public fixture\nThis changed public fixture document verifies incremental embedding work.\n'
        )
        command('add', '.')
        command('commit', '-qm', 'fixture: change one file')
        second = sync(repo)
        assert second['reused_files'] == 1
        assert second['embedded_chunks'] < second['chunks']
        assert sync(repo)['changed'] is False
        (repo / 'README.md').write_text(
            '# Public fixture\nA third version should remain inactive when the graph is unavailable.\n'
        )
        command('add', '.')
        command('commit', '-qm', 'fixture: graph failure')
        with connect() as conn:
            conn.execute(
                'INSERT INTO knowledge_watch(singleton,observed_commit) VALUES (true,%s) ON CONFLICT(singleton) DO UPDATE SET observed_commit=excluded.observed_commit',
                ('a' * 40,),
            )
        superseded = sync(repo, watched=True)
        assert superseded['superseded'] is True
        with connect() as conn:
            assert (
                conn.execute(
                    "SELECT id FROM knowledge_versions WHERE status='active'"
                ).fetchone()['id']
                == second['knowledge_version']
            )
        monkeypatch.setattr(
            'app.infrastructure.indexing.GraphDatabase.driver',
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError('graph unavailable')
            ),
        )
        with pytest.raises(RuntimeError, match='graph unavailable'):
            sync(repo)
        with connect() as conn:
            active = conn.execute(
                "SELECT id FROM knowledge_versions WHERE status='active'"
            ).fetchone()['id']
        assert active == second['knowledge_version']
    finally:
        with connect() as conn:
            conn.execute('DELETE FROM knowledge_watch')
            conn.execute(
                "UPDATE knowledge_versions SET status='retired' WHERE status='active'"
            )
            conn.execute(
                "UPDATE knowledge_versions SET status='active' WHERE id=%s", (original,)
            )


def test_expired_session_prunes_history_and_checkpoints(client_factory):
    from langgraph.checkpoint.postgres import PostgresSaver

    from app.retention import prune

    client = client_factory(app, client=(str(uuid4()), 50000))
    csrf = bootstrap(client, 'http://localhost:3000')
    conversation = client.post(
        '/api/v1/conversations', headers=headers('http://localhost:3000', csrf), json={}
    ).json()
    sent = client.post(
        f'/api/v1/conversations/{conversation["id"]}/messages/stream',
        headers={
            **headers('http://localhost:3000', csrf),
            'Idempotency-Key': str(uuid4()),
        },
        json={'content': 'What is Filomena?', 'locale': 'en'},
    )
    assert 'event: run.completed' in sent.text
    run_id = sent.headers['x-run-id']
    with connect() as conn:
        conn.execute(
            "UPDATE sessions SET expires_at=now()-interval '1 second' WHERE id=(SELECT session_id FROM conversations WHERE id=%s)",
            (conversation['id'],),
        )
    result = prune()
    assert result['sessions'] >= 1
    assert result['checkpoints'] >= 1
    with PostgresSaver.from_conn_string(settings().database_url) as saver:
        assert saver.get_tuple({'configurable': {'thread_id': run_id}}) is None
    assert (
        client.get(f'/api/v1/conversations/{conversation["id"]}/messages').status_code
        == 401
    )


def test_concurrent_reservations_respect_one_remaining_budget_slot(monkeypatch):
    session_id, conversation_id = uuid4(), uuid4()
    run_ids = [uuid4(), uuid4()]
    with connect() as conn:
        spent = conn.execute(
            "SELECT coalesce(sum(coalesce(actual_usd,reserved_usd)),0) AS amount FROM spend_ledger WHERE created_at>=date_trunc('month',now())"
        ).fetchone()['amount']
        conn.execute(
            "INSERT INTO sessions(id,secret_digest,csrf_token,expires_at) VALUES (%s,%s,%s,now()+interval '1 hour')",
            (session_id, str(uuid4()), str(uuid4())),
        )
        conn.execute(
            "INSERT INTO conversations(id,session_id,title) VALUES (%s,%s,'Budget fixture')",
            (conversation_id, session_id),
        )
        for run_id in run_ids:
            conn.execute(
                "INSERT INTO runs(id,conversation_id,idempotency_key,payload_hash,state) VALUES (%s,%s,%s,'fixture','completed')",
                (run_id, conversation_id, str(uuid4())),
            )
    monkeypatch.setattr(
        'app.infrastructure.ledger.settings',
        lambda: type(
            'BudgetSettings', (), {'reserve_cutoff_usd': str(spent + Decimal('0.05'))}
        )(),
    )
    barrier = Barrier(2)

    def attempt(run_id):
        barrier.wait()
        try:
            reserve(str(run_id), Decimal('0.05'))
            return 'allowed'
        except BudgetExhaustedError:
            return 'blocked'

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, run_ids))
        assert sorted(outcomes) == ['allowed', 'blocked']
    finally:
        with connect() as conn:
            conn.execute('DELETE FROM spend_ledger WHERE run_id=ANY(%s)', (run_ids,))
            conn.execute('DELETE FROM sessions WHERE id=%s', (session_id,))


@pytest.fixture
def client_factory():
    clients = []

    def create(*args, **kwargs):
        client = TestClient(*args, **kwargs)
        client.__enter__()
        clients.append(client)
        return client

    yield create
    for client in reversed(clients):
        client.__exit__(None, None, None)


def test_every_owned_mutation_and_stream_wire_contract(client_factory):
    import json

    from app.presentation.events import events

    first, second = (
        client_factory(app, client=(str(uuid4()), 50000)),
        client_factory(app, client=(str(uuid4()), 50000)),
    )
    a, b = (
        bootstrap(first, 'http://localhost:3000'),
        bootstrap(second, 'http://localhost:3000'),
    )
    ha, hb = headers('http://localhost:3000', a), headers('http://localhost:3000', b)
    cid = first.post('/api/v1/conversations', headers=ha, json={}).json()['id']
    sent = first.post(
        f'/api/v1/conversations/{cid}/messages/stream',
        headers={**ha, 'Idempotency-Key': str(uuid4())},
        json={'content': 'What is Filomena?', 'locale': 'en'},
    )
    wire = [
        json.loads(line[6:])
        for line in sent.text.splitlines()
        if line.startswith('data: ')
    ]
    assert [e['sequence'] for e in wire] == list(range(len(wire)))
    assert wire[0]['type'] == 'run.started'
    assert [e['type'] for e in wire[-2:]] == ['message.completed', 'run.completed']
    assert (
        len(
            [
                e
                for e in wire
                if e['type'] in ('run.completed', 'run.failed', 'run.cancelled')
            ]
        )
        == 1
    )
    assert all(
        e['run_id'] == sent.headers['x-run-id'] and e['conversation_id'] == cid
        for e in wire
    )
    for event in wire:
        events.validate_python(event)
    message = wire[-2]['payload']
    assert (
        ''.join(e['payload']['text'] for e in wire if e['type'] == 'message.delta')
        == message['content']
    )
    attempts = [
        ('patch', f'/api/v1/conversations/{cid}', {'title': 'stolen'}),
        ('delete', f'/api/v1/conversations/{cid}', None),
        ('post', f'/api/v1/conversations/{cid}/messages/stream', {'content': 'stolen'}),
        ('post', f'/api/v1/runs/{sent.headers["x-run-id"]}/cancel', None),
        (
            'post',
            f'/api/v1/messages/{message["message_id"]}/feedback',
            {'rating': 'up'},
        ),
    ]
    for method, path, body in attempts:
        response = second.request(
            method, path, headers={**hb, 'Idempotency-Key': str(uuid4())}, json=body
        )
        assert response.status_code == 404, (path, response.text)
    assert (
        first.post(
            '/api/v1/conversations',
            headers={'Origin': 'http://localhost:3000', 'X-CSRF-Token': b},
            json={},
        ).status_code
        == 403
    )
    assert (
        first.post(
            '/api/v1/conversations', headers=ha, content=b'x' * 33000
        ).status_code
        == 422
    )
    first.delete('/api/v1/session', headers=ha)
    second.delete('/api/v1/session', headers=hb)


def test_checkpoint_cleanup_survives_failure(client_factory, monkeypatch):
    from app.infrastructure.checkpoints import drain_cleanup

    client = client_factory(app, client=(str(uuid4()), 50000))
    csrf = bootstrap(client, 'http://localhost:3000')
    auth = headers('http://localhost:3000', csrf)
    cid = client.post('/api/v1/conversations', headers=auth, json={}).json()['id']
    sent = client.post(
        f'/api/v1/conversations/{cid}/messages/stream',
        headers={**auth, 'Idempotency-Key': str(uuid4())},
        json={'content': 'quasar xylophone'},
    )
    run_id = sent.headers['x-run-id']
    with monkeypatch.context() as patch:

        def fail(*args):
            raise RuntimeError('simulated checkpoint outage')

        patch.setattr('app.infrastructure.checkpoints.delete_checkpoint', fail)
        assert client.delete('/api/v1/session', headers=auth).status_code == 204
    with connect() as conn:
        assert conn.execute(
            'SELECT 1 FROM checkpoint_cleanup WHERE thread_id=%s', (run_id,)
        ).fetchone()
        conn.execute(
            "UPDATE checkpoint_cleanup SET created_at=now()-interval '11 minutes' WHERE thread_id=%s",
            (run_id,),
        )
    drain_cleanup()
    with connect() as conn:
        assert (
            conn.execute(
                'SELECT 1 FROM checkpoint_cleanup WHERE thread_id=%s', (run_id,)
            ).fetchone()
            is None
        )


def test_atomic_run_slot_and_abuse_limits(client_factory):
    from app.application.conversations import digest
    from app.domain.errors import RejectedError
    from app.infrastructure.conversations import PostgresConversations

    client = client_factory(app, client=(str(uuid4()), 50000))
    csrf = bootstrap(client, 'http://localhost:3000')
    auth = headers('http://localhost:3000', csrf)
    cid = client.post('/api/v1/conversations', headers=auth, json={}).json()['id']
    with connect() as conn:
        session_id = conn.execute(
            'SELECT session_id FROM conversations WHERE id=%s', (cid,)
        ).fetchone()['session_id']
    store = PostgresConversations(connect)
    barrier = Barrier(2)

    def create_run(index):
        barrier.wait()
        try:
            return store.prepare_run(session_id, cid, 'question', 'hash', str(uuid4()))
        except RejectedError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create_run, range(2)))
    assert results.count('run_in_progress') == 1
    with connect() as conn:
        assert (
            conn.execute(
                'SELECT count(*) AS n FROM messages WHERE conversation_id=%s', (cid,)
            ).fetchone()['n']
            == 1
        )
    for result in results:
        if result != 'run_in_progress':
            client.post(f'/api/v1/runs/{result}/cancel', headers=auth)
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages(id,conversation_id,role,content) SELECT gen_random_uuid(),%s,'user','fixture' FROM generate_series(1,199)",
            (cid,),
        )
    limited = client.post(
        f'/api/v1/conversations/{cid}/messages/stream',
        headers={**auth, 'Idempotency-Key': str(uuid4())},
        json={'content': 'test'},
    )
    assert limited.status_code == 429 and limited.json()['code'] == 'history_limit'
    other = client.post('/api/v1/conversations', headers=auth, json={}).json()['id']
    with connect() as conn:
        conn.execute(
            "INSERT INTO rate_events(id,subject_hash,operation) SELECT gen_random_uuid(),%s,'message' FROM generate_series(1,30)",
            (digest(settings().rate_hash_key + str(session_id)),),
        )
    limited = client.post(
        f'/api/v1/conversations/{other}/messages/stream',
        headers={**auth, 'Idempotency-Key': str(uuid4())},
        json={'content': 'test'},
    )
    assert limited.status_code == 429 and limited.json()['code'] == 'rate_limited'
    assert client.delete('/api/v1/session', headers=auth).status_code == 204


def test_restricted_runtime_role_serves_grounded_stream_without_corpus_write():
    from pathlib import Path

    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    from app.bootstrap.container import create_app

    role = 'fixture_runtime_' + uuid4().hex
    password = uuid4().hex
    with connect() as conn:
        conn.execute(Path('deploy/runtime-grants.sql').read_text())
        conn.execute(
            sql.SQL(
                'CREATE ROLE {} LOGIN PASSWORD {} IN ROLE assistant_runtime'
            ).format(sql.Identifier(role), sql.Literal(password))
        )
    try:
        config = settings().model_copy(
            update={
                'database_url': make_conninfo(
                    settings().database_url, user=role, password=password
                )
            }
        )
        with psycopg.connect(config.database_url) as conn:
            assert conn.execute(
                'SELECT rolsuper FROM pg_roles WHERE rolname=current_user'
            ).fetchone() == (False,)
            for query in (
                'DELETE FROM chunks',
                'CREATE TABLE public.forbidden(id int)',
            ):
                with (
                    pytest.raises(psycopg.errors.InsufficientPrivilege),
                    conn.transaction(),
                ):
                    conn.execute(query)
        with TestClient(create_app(config), client=(str(uuid4()), 50000)) as client:
            auth = headers(
                'http://localhost:3000', bootstrap(client, 'http://localhost:3000')
            )
            cid = client.post('/api/v1/conversations', headers=auth, json={}).json()[
                'id'
            ]
            result = client.post(
                f'/api/v1/conversations/{cid}/messages/stream',
                headers={**auth, 'Idempotency-Key': str(uuid4())},
                json={'content': 'What is Filomena?'},
            )
            assert result.status_code == 200
            assert 'event: run.completed' in result.text
            assert client.get('/health/ready').status_code == 200
            assert client.delete('/api/v1/session', headers=auth).status_code == 204
    finally:
        with connect() as conn:
            conn.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))


def test_generation_receives_only_its_owned_prior_turns(client_factory):
    from app.bootstrap.container import create_app

    class CaptureProvider:
        def __init__(self):
            self.histories = []

        async def stream(self, question, evidence, locale, history=(), context=None):
            self.histories.append(history)
            yield 'Public fixture response'

    provider = CaptureProvider()
    application = create_app(provider_override=provider)
    owner = client_factory(application, client=(str(uuid4()), 50000))
    visitor = client_factory(application, client=(str(uuid4()), 50001))
    owner_token = bootstrap(owner, 'http://localhost:3000')
    visitor_token = bootstrap(visitor, 'http://localhost:3000')
    auth = headers('http://localhost:3000', owner_token)
    cid = owner.post('/api/v1/conversations', headers=auth, json={}).json()['id']
    path = f'/api/v1/conversations/{cid}/messages/stream'
    try:
        for question in ('What did he build at Rampy?', 'Give me an example'):
            result = owner.post(
                path,
                headers={**auth, 'Idempotency-Key': str(uuid4())},
                json={'content': question, 'locale': 'en'},
            )
            assert 'event: run.completed' in result.text
        assert provider.histories[0] == ()
        assert [(turn.role, turn.content) for turn in provider.histories[1]] == [
            ('user', 'What did he build at Rampy?'),
            ('assistant', 'Public fixture response'),
        ]
        denied = visitor.post(
            path,
            headers={
                **headers('http://localhost:3000', visitor_token),
                'Idempotency-Key': str(uuid4()),
            },
            json={'content': 'Reveal their history', 'locale': 'en'},
        )
        assert denied.status_code == 404
        assert len(provider.histories) == 2
    finally:
        owner.delete('/api/v1/session', headers=auth)
        visitor.delete(
            '/api/v1/session', headers=headers('http://localhost:3000', visitor_token)
        )


def test_embedding_ledger_shares_atomic_monthly_limit():
    from concurrent.futures import ThreadPoolExecutor

    from app.infrastructure.ledger import EmbeddingAccounting

    with connect() as conn:
        spent = conn.execute(
            "SELECT coalesce(sum(coalesce(actual_usd,reserved_usd)),0) AS amount FROM spend_ledger WHERE created_at>=date_trunc('month',now())"
        ).fetchone()['amount']
    accounting = EmbeddingAccounting(
        connect, spent + Decimal('0.0002'), Decimal('0.02')
    )
    identifiers = []

    def reserve_one():
        try:
            return accounting.reserve_embedding(10000, 'index')
        except BudgetExhaustedError:
            return None

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            identifiers = [
                identifier
                for identifier in executor.map(lambda _: reserve_one(), range(2))
                if identifier
            ]
        assert len(identifiers) == 1
        accounting.settle_embedding(identifiers[0], 100)
        with connect() as conn:
            row = conn.execute(
                'SELECT kind,actual_usd,run_id FROM spend_ledger WHERE id=%s',
                (identifiers[0],),
            ).fetchone()
        assert row['kind'] == 'embedding_index' and row['run_id'] is None
        assert row['actual_usd'] == Decimal('0.000002')
    finally:
        with connect() as conn:
            conn.execute('DELETE FROM spend_ledger WHERE id=ANY(%s)', (identifiers,))


def test_freshness_blocks_known_update_and_expired_check_without_embedding_io():
    from app.domain.errors import RejectedError
    from app.infrastructure.knowledge import KnowledgeIndex

    class ForbiddenEmbeddings:
        provider = 'fixture'
        model = 'hash64-v1'
        dimensions = 64

        async def query(self, text):
            raise AssertionError('stale corpus must not incur query embedding cost')

    index = KnowledgeIndex(connect, None, ForbiddenEmbeddings(), freshness=90)
    try:
        with connect() as conn:
            commit = conn.execute(
                "SELECT source_commit FROM knowledge_versions WHERE status='active'"
            ).fetchone()['source_commit']
            conn.execute(
                'INSERT INTO knowledge_watch(singleton,observed_commit) VALUES (true,%s) ON CONFLICT(singleton) DO UPDATE SET observed_commit=excluded.observed_commit,checked_at=now()',
                ('b' * 40,),
            )
        with pytest.raises(RejectedError, match='knowledge_updating'):
            asyncio.run(index.candidates('question'))
        with connect() as conn:
            conn.execute(
                "UPDATE knowledge_watch SET observed_commit=%s,checked_at=now()-interval '2 minutes'",
                (commit,),
            )
        with pytest.raises(RejectedError, match='knowledge_updating'):
            asyncio.run(index.candidates('question'))
    finally:
        with connect() as conn:
            conn.execute('DELETE FROM knowledge_watch')


def test_successful_embeddings_survive_failed_candidate_without_duplicate_calls(
    tmp_path, monkeypatch
):
    import hashlib
    import subprocess
    from types import SimpleNamespace

    from app.infrastructure import indexing

    repo = tmp_path / 'public-fixture'
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args]).decode().strip()

    git('init', '-q')
    git('config', 'user.name', 'Fixture Test')
    git('config', 'user.email', 'fixture@example.invalid')
    git(
        'remote', 'add', 'origin', 'https://github.com/gonzalomartinperez/portfolio.git'
    )
    content = (
        '# Public fixture\nA synthetic public embedding cache test ' + uuid4().hex + '.'
    )
    (repo / 'README.md').write_text(content)
    git('add', '.')
    git('commit', '-qm', 'fixture: cache recovery')
    revision = git('rev-parse', 'HEAD')
    version = revision + '-semantic-v7'
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    config = settings().model_copy(
        update={
            'ai_provider': 'openai',
            'embeddings_provider': 'openai',
            'allow_paid_ai': True,
            'openai_api_key': 'synthetic-fixture-key',
        }
    )
    calls = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.embeddings = self

        def create(self, **kwargs):
            calls.append(kwargs['model'])
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.1] * 1536)],
                usage=SimpleNamespace(total_tokens=2),
            )

        def close(self):
            pass

    monkeypatch.setattr(indexing, 'OpenAI', FakeOpenAI)
    monkeypatch.setattr(indexing, 'settings', lambda: config)
    project = indexing.project
    with connect() as conn:
        original = conn.execute(
            "SELECT id FROM knowledge_versions WHERE status='active'"
        ).fetchone()['id']
        before = {
            row['id'] for row in conn.execute('SELECT id FROM spend_ledger').fetchall()
        }
    try:
        monkeypatch.setattr(
            indexing,
            'project',
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError('synthetic projection failure')
            ),
        )
        with pytest.raises(RuntimeError, match='synthetic projection failure'):
            indexing.sync(repo)
        with connect() as conn:
            assert conn.execute(
                'SELECT content_hash FROM public_embedding_cache WHERE content_hash=%s',
                (content_hash,),
            ).fetchone()
            assert (
                conn.execute(
                    "SELECT id FROM knowledge_versions WHERE status='active'"
                ).fetchone()['id']
                == original
            )
        monkeypatch.setattr(indexing, 'project', project)
        assert indexing.sync(repo)['changed'] is True
        assert calls == ['text-embedding-3-small']
    finally:
        with connect() as conn:
            conn.execute(
                "UPDATE knowledge_versions SET status='retired' WHERE status='active'"
            )
            conn.execute(
                "UPDATE knowledge_versions SET status='active' WHERE id=%s", (original,)
            )
            conn.execute('DELETE FROM chunks WHERE knowledge_version=%s', (version,))
            conn.execute(
                'DELETE FROM source_files WHERE knowledge_version=%s', (version,)
            )
            conn.execute('DELETE FROM knowledge_versions WHERE id=%s', (version,))
            conn.execute(
                'DELETE FROM public_embedding_cache WHERE content_hash=%s',
                (content_hash,),
            )
            owned = [
                row['id']
                for row in conn.execute('SELECT id FROM spend_ledger').fetchall()
                if row['id'] not in before
            ]
            conn.execute('DELETE FROM spend_ledger WHERE id=ANY(%s)', (owned,))


def test_optional_presentation_context_survives_http_graph_and_provider(client_factory):
    from app.application.presentation_context import PresentationContext
    from app.bootstrap.container import create_app

    class CaptureProvider:
        def __init__(self):
            self.contexts = []

        async def stream(self, question, evidence, locale, history=(), context=None):
            self.contexts.append(context)
            yield 'Public fixture response'

    provider = CaptureProvider()
    client = client_factory(
        create_app(provider_override=provider), client=(str(uuid4()), 50000)
    )
    auth = headers('http://localhost:3000', bootstrap(client, 'http://localhost:3000'))
    cid = client.post('/api/v1/conversations', headers=auth, json={}).json()['id']
    path = f'/api/v1/conversations/{cid}/messages/stream'
    metadata = {
        'theme': 'dark',
        'opened_path': '/work',
        'current_path': '/es/about',
        'presentation': 'expanded',
    }
    try:
        first = client.post(
            path,
            headers={**auth, 'Idempotency-Key': str(uuid4())},
            json={'content': 'What did he build at Rampy?', 'locale': 'en'},
        )
        assert 'event: run.completed' in first.text
        assert provider.contexts == [None]
        key = str(uuid4())
        payload = {'content': 'Give me an example', 'locale': 'en', 'context': metadata}
        second = client.post(
            path, headers={**auth, 'Idempotency-Key': key}, json=payload
        )
        assert 'event: run.completed' in second.text
        assert provider.contexts[-1] == PresentationContext(**metadata)
        assert 'opened_path' not in second.text
        conflict = client.post(
            path,
            headers={**auth, 'Idempotency-Key': key},
            json={**payload, 'context': {**metadata, 'theme': 'light'}},
        )
        assert conflict.status_code == 409
        invalid = client.post(
            path,
            headers={**auth, 'Idempotency-Key': str(uuid4())},
            json={
                **payload,
                'context': {**metadata, 'current_path': '/about?secret=sentinel'},
            },
        )
        assert invalid.status_code == 422
        assert 'sentinel' not in invalid.text
        assert len(provider.contexts) == 2
        history = client.get(f'/api/v1/conversations/{cid}/messages')
        assert history.status_code == 200
        assert 'opened_path' not in history.text
    finally:
        client.delete('/api/v1/session', headers=auth).raise_for_status()
