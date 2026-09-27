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
        reserve(str(uuid4()), Decimal('9.01'))
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
