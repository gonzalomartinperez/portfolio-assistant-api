import asyncio
import hashlib
from decimal import Decimal

import pytest

from app.bootstrap.config import Settings
from app.domain.budget import Budget
from app.infrastructure.migrations import validate_history
from app.presentation.middleware import BodyLimit


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '0'])
def test_invalid_money_fails_closed(value):
    with pytest.raises(ValueError):
        Settings(monthly_budget_usd=value)


def test_reservation_covers_bounded_request_and_cutoff():
    with pytest.raises(ValueError, match='bounded maximum'):
        Settings(reservation_usd='0.001')
    with pytest.raises(ValueError, match='monthly budget'):
        Settings(monthly_budget_usd='1')
    policy = Budget(
        Decimal(10), Decimal(9), Decimal('.05'), Decimal('.1'), Decimal('.5')
    )
    assert policy.cost(1000, 500) == Decimal('.00035')
    with pytest.raises(ValueError):
        policy.cost(-1, 0)


def test_migration_missing_modified_and_out_of_order_fail(tmp_path):
    first, second = tmp_path / '001_first.sql', tmp_path / '002_second.sql'
    first.write_text('SELECT 1;')
    second.write_text('SELECT 2;')
    checksum = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    validate_history([first, second], {first.name: checksum(first)})
    with pytest.raises(RuntimeError, match='missing'):
        validate_history([first], {second.name: checksum(second)})
    with pytest.raises(RuntimeError, match='prefix'):
        validate_history([first, second], {second.name: checksum(second)})
    with pytest.raises(RuntimeError, match='checksum'):
        validate_history([first, second], {first.name: 'changed'})
    with pytest.raises(RuntimeError, match='order'):
        validate_history([second, first], {})


def test_chunked_request_is_bounded_before_parser():
    async def run():
        invoked = False

        async def app(scope, receive, send):
            nonlocal invoked
            invoked = True

        chunks = [
            {'type': 'http.request', 'body': b'a' * 20, 'more_body': True},
            {'type': 'http.request', 'body': b'b' * 20, 'more_body': False},
        ]
        sent = []

        async def receive():
            return chunks.pop(0)

        async def send(message):
            sent.append(message)

        await BodyLimit(app, maximum=32)(
            {'type': 'http', 'method': 'POST'}, receive, send
        )
        assert sent[0]['status'] == 422
        assert not invoked
        assert b'a' * 20 not in sent[1]['body']

    asyncio.run(run())


def test_production_cookie_and_error_redaction(capsys):
    from datetime import UTC, datetime
    from uuid import uuid4

    from fastapi.testclient import TestClient

    from app.bootstrap.container import create_app
    from app.domain.conversations import Session

    config = Settings(
        environment='production',
        secure_cookies=True,
        allowed_origins='https://portfolio.example',
        database_url='postgresql://fixture_user:fixture-password@database/fixture',
        neo4j_uri='bolt://graph:7687',
        neo4j_password='fixture-password',
        rate_hash_key='fixture-only-production-test-value-32',
    )

    class Service:
        broken = False

        def bootstrap(self, subject):
            if self.broken:
                raise RuntimeError('synthetic-secret-canary')
            return 'synthetic-cookie-value', Session(
                uuid4(), 'synthetic-csrf', datetime.now(UTC)
            )

    app = create_app(config)
    service = Service()
    app.state.conversations = service
    client = TestClient(app, base_url='https://api.example')
    headers = {'Origin': 'https://portfolio.example', 'X-Session-Bootstrap': '1'}
    response = client.post('/api/v1/session', headers=headers, json={})
    cookie = response.headers['set-cookie']
    assert '__Host-assistant_session=' in cookie
    assert 'HttpOnly' in cookie and 'Secure' in cookie and 'SameSite=lax' in cookie
    assert 'Domain=' not in cookie and 'Path=/' in cookie
    service.broken = True
    failed = client.post('/api/v1/session', headers=headers, json={})
    assert failed.status_code == 503
    assert failed.json()['code'] == 'dependency_unavailable'
    assert 'synthetic-secret-canary' not in failed.text + capsys.readouterr().err


def test_database_error_translation_never_passes_driver_exception_to_use_case():
    from contextlib import contextmanager

    import psycopg

    from app.domain.errors import DependencyUnavailableError
    from app.infrastructure.db import translated

    @contextmanager
    def broken():
        raise psycopg.OperationalError('synthetic-private-dsn')
        yield

    with pytest.raises(DependencyUnavailableError) as error, translated(broken)():
        pass
    assert str(error.value) == 'storage_unavailable'


def test_checkpoint_cleanup_uses_injected_database(monkeypatch):
    from contextlib import contextmanager

    from app.infrastructure import checkpoints

    statements, destinations = [], []

    class Connection:
        def execute(self, sql, params=()):
            statements.append((sql, params))
            return self

        def fetchall(self):
            return [{'thread_id': 'fixture-run'}]

    @contextmanager
    def connection():
        yield Connection()

    monkeypatch.setattr(
        checkpoints,
        'delete_checkpoint',
        lambda thread, database_url: destinations.append((thread, database_url)),
    )
    assert (
        checkpoints.drain_cleanup(
            connection=connection, database_url='synthetic-db', limit=1
        )
        == 1
    )
    assert destinations == [('fixture-run', 'synthetic-db')]
    assert statements[0][1] == (1,)
