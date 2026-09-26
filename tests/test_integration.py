import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from neo4j import GraphDatabase

from app.config import settings
from app.db import connect
from app.knowledge import embed
from app.main import app, retrieve
from app.migrate import main as migrate

pytestmark = pytest.mark.skipif(os.getenv('TEST_INTEGRATION') != '1', reason='requires real PostgreSQL and Neo4j')


def headers(origin: str, csrf: str) -> dict:
    return {'Origin': origin, 'X-CSRF-Token': csrf}


def bootstrap(client: TestClient, origin: str):
    response = client.post('/api/v1/session', headers={'Origin': origin, 'X-Session-Bootstrap': '1'}, json={})
    assert response.status_code == 200
    return response.json()['csrf_token']


def test_sessions_stream_idempotency_and_ownership():
    migrate()
    first = TestClient(app)
    second = TestClient(app)
    a = bootstrap(first, 'http://localhost:3000')
    b = bootstrap(second, 'http://localhost:3001')
    conv = first.post('/api/v1/conversations', headers=headers('http://localhost:3000', a), json={})
    assert conv.status_code == 200
    cid = conv.json()['id']
    assert second.get(f'/api/v1/conversations/{cid}/messages').status_code == 404
    assert first.patch(f'/api/v1/conversations/{cid}', headers={'Origin': 'http://localhost:3000'}, json={'title': 'x'}).status_code == 403
    key = str(uuid4())
    payload = {'content': 'What is Filomena?', 'locale': 'en'}
    sent = first.post(f'/api/v1/conversations/{cid}/messages/stream', headers={**headers('http://localhost:3000', a), 'Idempotency-Key': key}, json=payload)
    assert sent.status_code == 200
    assert 'event: run.completed' in sent.text
    assert 'event: message.completed' in sent.text
    duplicate = first.post(f'/api/v1/conversations/{cid}/messages/stream', headers={**headers('http://localhost:3000', a), 'Idempotency-Key': key}, json=payload)
    assert duplicate.status_code == 409
    assert second.get(f'/api/v1/runs/{sent.headers["x-run-id"]}').status_code == 404
    saved = first.get(f'/api/v1/conversations/{cid}/messages').json()['items']
    assert len(saved) == 2
    assert saved[0]['citations'][0]['url'].startswith('https://github.com/gonzalomartinperez/portfolio/blob/')
    assert first.delete('/api/v1/session', headers=headers('http://localhost:3000', a)).status_code == 204
    assert first.get(f'/api/v1/conversations/{cid}/messages').status_code == 401
    second.delete('/api/v1/session', headers=headers('http://localhost:3001', b))


def test_real_vector_and_graph():
    with connect() as conn:
        count = conn.execute("SELECT count(*) AS n FROM chunks c JOIN knowledge_versions v ON v.id=c.knowledge_version WHERE v.status='active' AND c.embedding <=> %s::vector IS NOT NULL", (embed('Filomena'),)).fetchone()['n']
    assert count > 0
    rows, commits = retrieve('What is Filomena?')
    assert len(rows) > 0 and len(commits[0]) == 40
    driver = GraphDatabase.driver(settings().neo4j_uri, auth=(settings().neo4j_user, settings().neo4j_password))
    try:
        with driver.session() as session:
            result = session.run('MATCH (:Project {name:$name})-[:SUPPORTED_BY]->(d:Document) RETURN count(d) AS n', name='Filomena').single()
            assert result['n'] > 0
    finally:
        driver.close()
