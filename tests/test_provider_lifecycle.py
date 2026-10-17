"""Exercise the actual API lifespan with isolated resources and failing cleanup."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.bootstrap import container
from app.bootstrap.config import Settings


@pytest.mark.parametrize(
    'failure', [None, 'runs', 'client', 'embedding', 'multiple', 'startup', 'cancel']
)
def test_lifespan_attempts_all_owned_cleanup_and_preserves_failures(
    monkeypatch, failure
):
    closed = []

    def close(name):
        def operation(*args, **kwargs):
            closed.append(name)
            if failure == 'cancel' and name == 'client':
                raise asyncio.CancelledError('synthetic-cancel')
            if failure == name or (
                failure == 'multiple' and name in ('client', 'graph')
            ):
                raise RuntimeError('synthetic-' + name)

        return operation

    def resource(name, *, asynchronous=False):
        value = Mock()
        if asynchronous:
            value.open = AsyncMock()
            value.close = AsyncMock(side_effect=close(name))
        else:
            value.close.side_effect = close(name)
        return value

    database = resource('database')
    checkpoints = resource('checkpoints', asynchronous=True)
    graph = resource('graph')
    client = resource('client', asynchronous=True)
    embedding = resource('embedding')
    observer = resource('observer', asynchronous=True)
    runs = Mock()
    runs.drain_cleanup = AsyncMock(side_effect=close('runs'))
    monkeypatch.setattr(container, 'pool', Mock(return_value=database))
    monkeypatch.setattr(
        container, 'AsyncConnectionPool', Mock(return_value=checkpoints)
    )
    monkeypatch.setattr(
        container, 'GraphDatabase', Mock(driver=Mock(return_value=graph))
    )
    monkeypatch.setattr(
        container, 'create_async_client', AsyncMock(return_value=client)
    )
    monkeypatch.setattr(container, 'create_sync_client', Mock(return_value=embedding))
    for name in (
        'LocalLanguageDetector',
        'ResponsesProvider',
        'PostgresAccounting',
        'OpenAIEmbeddings',
        'EmbeddingAccounting',
        'KnowledgeIndex',
        'PostgresProductAnalytics',
        'PostgresFeedback',
        'AsyncPostgresSaver',
        'LangGraphWorkflow',
        'PublicRetrieval',
        'PostgresConversations',
        'Conversations',
        'PostgresOperations',
        'PostgresRuns',
    ):
        monkeypatch.setattr(container, name, Mock())
    monkeypatch.setattr(container, 'OperationalObserver', Mock(return_value=observer))
    monkeypatch.setattr(container, 'RunService', Mock(return_value=runs))
    if failure == 'startup':
        container.create_sync_client.side_effect = RuntimeError('synthetic-startup')
    config = Settings(_env_file=None).model_copy(
        update={
            'ai_provider': 'openai',
            'embeddings_provider': 'openai',
            'allow_paid_ai': True,
            'openai_api_key': 'synthetic-fixture-only',
            'ops_read_token': 'synthetic-ops-token',
            'otel_sdk_disabled': True,
        }
    )
    app = container.create_app(config)

    async def run():
        async with app.router.lifespan_context(app):
            assert not closed

    if failure:
        with pytest.raises(
            ExceptionGroup
            if failure == 'multiple'
            else asyncio.CancelledError
            if failure == 'cancel'
            else RuntimeError
        ) as raised:
            asyncio.run(run())
        messages = []
        error = raised.value
        while error is not None:
            messages.append(str(error))
            error = error.__context__
        if failure == 'multiple':
            assert [str(error) for error in raised.value.exceptions] == [
                'synthetic-client',
                'synthetic-graph',
            ]
        else:
            assert messages == ['synthetic-' + failure]
    else:
        asyncio.run(run())
    expected = [
        'runs',
        'observer',
        'client',
        'embedding',
        'checkpoints',
        'graph',
        'database',
    ]
    if failure == 'startup':
        expected = ['client', 'checkpoints', 'graph', 'database']
    assert closed == expected
