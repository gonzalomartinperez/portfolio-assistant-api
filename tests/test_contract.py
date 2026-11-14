import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.fixture import fixture_message
from app.main import app


def test_offline_contract_and_live():
    client = TestClient(app)
    assert client.get('/health/live').json() == {'status': 'ok'}
    assert (
        '/api/v1/conversations/{conversation_id}/messages/stream'
        in app.openapi()['paths']
    )


def test_origin_rejected_without_db():
    client = TestClient(app)
    response = client.post(
        '/api/v1/session', headers={'Origin': 'https://evil.example'}
    )
    assert response.status_code == 403
    assert response.json()['code'] == 'origin_denied'


def test_fixture_evaluation_direct_multiple_source_unknown_and_adversarial():
    fixtures = json.loads(
        (Path(__file__).parent / 'fixtures/evaluation.json').read_text()
    )
    for case in fixtures:
        answer = fixture_message(case['question'], case['evidence'], case['locale'])
        assert case['contains'] in answer, case['name']
        assert case['excludes'] not in answer, case['name']
        if case['name'] == 'multiple public sources':
            assert answer.count('•') == 2


def test_committed_contracts_match_offline_generation():
    from contracts.export import artifacts

    for name, schema in artifacts().items():
        assert json.loads((Path('contracts') / name).read_text()) == schema


def test_stream_schema_rejects_internal_payloads():
    import pytest
    from pydantic import ValidationError

    from app.presentation.events import events

    base = {
        'type': 'message.delta',
        'schema_version': '1',
        'run_id': '00000000-0000-0000-0000-000000000001',
        'conversation_id': '00000000-0000-0000-0000-000000000002',
        'sequence': 0,
        'timestamp': '2026-09-27T00:00:00Z',
    }
    assert (
        events.validate_python({**base, 'payload': {'text': 'Hello'}}).payload.text
        == 'Hello'
    )
    with pytest.raises(ValidationError):
        events.validate_python(
            {**base, 'payload': {'text': 'Hello', 'internal_prompt': 'hidden'}}
        )


def test_committed_stream_examples_validate():
    from app.presentation.events import events

    examples = json.loads(Path('contracts/sse.examples.json').read_text())
    for event in [
        *examples['success_abstention'],
        examples['failure'],
        examples['cancelled'],
    ]:
        events.validate_python(event)


def health_client(ready, revision='unknown'):
    from fastapi import FastAPI

    from app.presentation.http import router

    probe = FastAPI()
    probe.include_router(router)
    probe.state.ready = ready
    probe.state.revision = revision
    return TestClient(probe)


def test_healthz_reports_revision_without_dependencies():
    def broken():
        raise RuntimeError('must not be called')

    sha = 'a' * 40
    assert health_client(broken, sha).get('/healthz').json() == {
        'status': 'ok',
        'version': sha,
    }
    assert TestClient(app).get('/healthz').json() == {
        'status': 'ok',
        'version': app.state.config.ops_api_commit or 'unknown',
    }


def test_readyz_success_and_stub_without_schema():
    sha = 'b' * 40
    assert health_client(lambda: '009', sha).get('/readyz').json() == {
        'status': 'ok',
        'version': sha,
        'schema_version': '009',
    }
    body = health_client(lambda: None).get('/readyz').json()
    assert body == {'status': 'ok', 'version': 'unknown', 'schema_version': None}
    assert health_client(lambda: '009').get('/health/ready').json() == {'status': 'ok'}


def test_readyz_failure_matches_health_ready():
    def broken():
        raise RuntimeError('secret detail')

    client = health_client(broken)
    legacy = client.get('/health/ready')
    current = client.get('/readyz')
    assert current.status_code == legacy.status_code == 503
    assert current.json() == legacy.json()
    assert 'secret detail' not in current.text
