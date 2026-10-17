"""Native SDK transport isolation and ownership without network or real credentials."""

import asyncio
from unittest.mock import AsyncMock, Mock

import httpx2
import pytest

from app.infrastructure import provider_http


@pytest.mark.parametrize('asynchronous', [False, True])
def test_transport_ignores_proxy_certificate_and_key_environment(
    monkeypatch, asynchronous
):
    for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'):
        monkeypatch.setenv(name, 'not-a-valid-proxy')
    for name in ('SSL_CERT_FILE', 'SSL_CERT_DIR'):
        monkeypatch.setenv(name, '/synthetic/nonexistent/certificate')
    monkeypatch.setenv('OPENAI_API_KEY', 'environment-key-must-not-be-used')

    def verify(client, timeout):
        assert str(client.base_url) == 'https://api.openai.com/v1/'
        assert client.api_key == 'synthetic-fixture-only'
        assert client.max_retries == 0
        assert client.timeout == timeout
        assert client._client.follow_redirects is False
        assert client._client.trust_env is False
        assert client._client.timeout.read == timeout
        assert not client._client.is_closed

    async def run():
        client = await provider_http.create_async_client(
            api_key='synthetic-fixture-only'
        )
        verify(client, 45)
        await client.close()
        assert client._client.is_closed

    if asynchronous:
        asyncio.run(run())
    else:
        client = provider_http.create_sync_client(api_key='synthetic-fixture-only')
        verify(client, 20)
        client.close()
        assert client._client.is_closed


@pytest.mark.parametrize('asynchronous', [False, True])
def test_constructor_failure_closes_unclaimed_transport(monkeypatch, asynchronous):
    transport = Mock()
    transport.aclose = AsyncMock()
    constructor = Mock(side_effect=ValueError('synthetic-construction-failure'))
    if asynchronous:
        monkeypatch.setattr(
            provider_http, 'DefaultAsyncHttpxClient', Mock(return_value=transport)
        )
        monkeypatch.setattr(provider_http, 'AsyncOpenAI', constructor)
        with pytest.raises(ValueError, match='synthetic-construction-failure'):
            asyncio.run(
                provider_http.create_async_client(api_key='synthetic-fixture-only')
            )
        transport.aclose.assert_awaited_once_with()
    else:
        monkeypatch.setattr(
            provider_http, 'DefaultHttpxClient', Mock(return_value=transport)
        )
        monkeypatch.setattr(provider_http, 'OpenAI', constructor)
        with pytest.raises(ValueError, match='synthetic-construction-failure'):
            provider_http.create_sync_client(api_key='synthetic-fixture-only')
        transport.close.assert_called_once_with()


@pytest.mark.parametrize('asynchronous', [False, True])
@pytest.mark.parametrize('key', [None, ''])
def test_missing_explicit_key_never_falls_back_to_environment(
    monkeypatch, asynchronous, key
):
    monkeypatch.setenv('OPENAI_API_KEY', 'environment-key-must-not-be-used')
    with pytest.raises(ValueError, match='provider API key is required'):
        if asynchronous:
            asyncio.run(provider_http.create_async_client(api_key=key))
        else:
            provider_http.create_sync_client(api_key=key)


@pytest.mark.parametrize('status', [307, 308])
@pytest.mark.parametrize('asynchronous', [False, True])
def test_redirect_never_forwards_request_body(monkeypatch, status, asynchronous):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx2.Response(
            status, headers={'Location': 'http://untrusted.invalid/collect'}
        )

    def factory(native):
        def construct(**kwargs):
            assert kwargs['verify'] is True
            assert kwargs['trust_env'] is False
            assert kwargs['follow_redirects'] is False
            assert 'limits' not in kwargs and 'http2' not in kwargs
            return native(transport=httpx2.MockTransport(handle), **kwargs)

        return construct

    async def run():
        client = await provider_http.create_async_client(
            api_key='synthetic-fixture-only'
        )
        try:
            response = await client._client.post(
                str(client.base_url) + 'responses',
                json={'input': 'private-fixture-body'},
            )
            assert response.status_code == status
        finally:
            await client.close()

    if asynchronous:
        monkeypatch.setattr(
            provider_http,
            'DefaultAsyncHttpxClient',
            factory(provider_http.DefaultAsyncHttpxClient),
        )
        asyncio.run(run())
    else:
        monkeypatch.setattr(
            provider_http,
            'DefaultHttpxClient',
            factory(provider_http.DefaultHttpxClient),
        )
        with provider_http.create_sync_client(
            api_key='synthetic-fixture-only'
        ) as client:
            response = client._client.post(
                str(client.base_url) + 'responses',
                json={'input': 'private-fixture-body'},
            )
            assert response.status_code == status
    assert len(requests) == 1
    assert requests[0].url.host == 'api.openai.com'
    assert b'private-fixture-body' in requests[0].content
