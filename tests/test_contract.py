from fastapi.testclient import TestClient

from app.main import app
from app.provider import OpenAIAdapter


def test_offline_contract_and_live():
    client = TestClient(app)
    assert client.get('/health/live').json() == {'status': 'ok'}
    assert '/api/v1/conversations/{conversation_id}/messages/stream' in app.openapi()['paths']


def test_origin_rejected_without_db():
    client = TestClient(app)
    response = client.post('/api/v1/session', headers={'Origin': 'https://evil.example'})
    assert response.status_code == 403
    assert response.json()['code'] == 'origin_denied'


async def simulated_client():
    class Client:
        async def create(self, **kwargs):
            return type('Response', (), {'output_text': kwargs['input'][1]['content']})()
    return Client()


def test_paid_adapter_fails_closed():
    import asyncio
    adapter = OpenAIAdapter(asyncio.run(simulated_client()))
    try:
        asyncio.run(adapter.complete('question', 'evidence'))
    except RuntimeError as exc:
        assert str(exc) == 'paid_ai_disabled'
    else:
        assert False, 'paid call must require opt-in'


def test_openai_adapter_uses_responses_contract_with_simulated_client(monkeypatch):
    import asyncio

    from app import provider

    class Enabled:
        allow_paid_ai = True
        ai_provider = 'openai'

    class Client:
        kwargs = None

        async def create(self, **kwargs):
            self.kwargs = kwargs
            return type('Response', (), {'output_text': 'Evidence-grounded answer'})()

    monkeypatch.setattr(provider, 'settings', lambda: Enabled())
    client = Client()
    answer = asyncio.run(OpenAIAdapter(client).complete('Question', 'Public evidence'))
    assert answer == 'Evidence-grounded answer'
    assert client.kwargs['model'] == 'gpt-6-luna'
    assert client.kwargs['input'][0]['role'] == 'developer'
    assert 'Public evidence' in client.kwargs['input'][1]['content']
