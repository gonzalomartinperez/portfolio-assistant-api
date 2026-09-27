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
