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
