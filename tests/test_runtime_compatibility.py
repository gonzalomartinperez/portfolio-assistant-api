"""Configuration and real SDK behavior across the fixed dependency review cohort."""

import asyncio
import json

import httpx
import pytest
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.adapters.providers.answer import ResponsesProvider
from app.application.contracts import GenerationFailedError
from app.bootstrap.config import Settings
from app.domain.errors import ProviderUnavailableError


def test_utf8_environment_configuration_and_environment_override(tmp_path, monkeypatch):
    configuration = tmp_path / 'fixture.env'
    configuration.write_text(
        'NEO4J_USER=lectura-pública\nRETENTION_DAYS=4\n'
        'AI_PROVIDER=fixture\nALLOW_PAID_AI=false\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('RETENTION_DAYS', '5')
    settings = Settings(_env_file=configuration, _env_file_encoding='utf-8')
    assert settings.neo4j_user == 'lectura-pública'
    assert settings.retention_days == 5
    assert settings.ai_provider == 'fixture' and not settings.allow_paid_ai
    assert settings.openai_model == 'gpt-6-luna'
    assert settings.openai_reasoning_effort == 'medium'


def test_environment_validation_keeps_model_and_paid_authorization_closed(monkeypatch):
    marker = 'unsupported-model-private-canary'
    monkeypatch.setenv('OPENAI_MODEL', marker)
    with pytest.raises(ValidationError) as failure:
        Settings(_env_file=None)
    assert marker not in str(failure.value)
    monkeypatch.setenv('OPENAI_MODEL', 'gpt-6-luna')
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    monkeypatch.setenv('ALLOW_PAID_AI', 'false')
    with pytest.raises(ValidationError, match='paid provider requires explicit'):
        Settings(_env_file=None)


@pytest.mark.parametrize('termination', ['eof', 'timeout', 'cancel'])
def test_real_sdk_partial_stream_closes_without_replaying_generation(termination):
    requests = []
    closed = []

    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            frame = {
                'type': 'response.output_text.delta',
                'sequence_number': 1,
                'item_id': 'msg_fixture',
                'output_index': 0,
                'content_index': 0,
                'delta': 'Partial answer.',
            }
            yield ('data: ' + json.dumps(frame) + '\n\n').encode()
            if termination == 'timeout':
                raise httpx.ReadTimeout('private-transport-canary')

        async def aclose(self):
            closed.append(True)

    def handle(request):
        requests.append(request)
        return httpx.Response(
            200, headers={'Content-Type': 'text/event-stream'}, stream=Body()
        )

    async def run():
        async with AsyncOpenAI(
            api_key='synthetic-fixture-only',
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
        ) as client:
            stream = ResponsesProvider(client, 'gpt-6-luna').stream(
                'Question', 'Approved public evidence', 'en'
            )
            assert await anext(stream) == 'Partial answer.'
            if termination == 'cancel':
                await stream.aclose()
            else:
                expected = (
                    ProviderUnavailableError
                    if termination == 'timeout'
                    else GenerationFailedError
                )
                with pytest.raises(expected) as failure:
                    await anext(stream)
                assert 'private-transport-canary' not in str(failure.value)
            assert closed
        assert len(requests) == 1

    asyncio.run(run())
