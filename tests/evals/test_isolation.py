"""The isolation guard rejects remote PostgreSQL and remote Neo4j."""

import pytest

from app.bootstrap.config import Settings
from evals.harness.isolation import (
    IsolationError,
    check_neo4j_uri,
    check_postgres_dsn,
    require_isolated,
)


@pytest.mark.parametrize(
    'dsn',
    [
        'postgresql://u:p@localhost:5432/db',
        'postgresql://u@127.0.0.1:5433/db',
        'postgresql://u@[::1]:5432/db',
        'postgresql://u@LOCALHOST/db',
        'postgresql:///db?host=/var/run/postgresql',
        'host=localhost dbname=db',
        'host=127.0.0.1,::1 dbname=db',
        'host=/tmp dbname=db',
    ],
)
def test_postgres_accepts_loopback_and_unix_sockets(dsn):
    check_postgres_dsn(dsn)


@pytest.mark.parametrize(
    'dsn',
    [
        'postgresql://user@db.example.com/db',
        'postgresql://u@10.0.0.5/db',
        'postgresql://u@localhost.evil.example/db',
        'postgresql://localhost,db.example.com/db',
        'host=localhost,db.example.com dbname=db',
        'postgresql://u@localhost/db?hostaddr=203.0.113.9',
        'postgresql:///db',
        'dbname=db',
        'postgresql://u@/db',
        'not a dsn ==',
        '',
    ],
)
def test_postgres_rejects_remote_missing_or_unparseable_hosts(dsn):
    with pytest.raises(IsolationError):
        check_postgres_dsn(dsn)


@pytest.mark.parametrize(
    'uri',
    [
        'bolt://127.0.0.1:7688',
        'neo4j://localhost:7687',
        'bolt://[::1]:7687',
        'bolt+s://localhost',
        'neo4j+ssc://127.0.0.1',
    ],
)
def test_neo4j_accepts_loopback(uri):
    check_neo4j_uri(uri)


@pytest.mark.parametrize(
    'uri',
    [
        'neo4j+s://x.databases.neo4j.io',
        'bolt://neo4j.example.com:7687',
        'bolt://192.168.1.10:7687',
        'bolt://localhost.evil.example',
        'bolt:///',
        'localhost:7687',
        'bolt://[::1',
        '',
    ],
)
def test_neo4j_rejects_remote_or_missing_hosts(uri):
    with pytest.raises(IsolationError):
        check_neo4j_uri(uri)


def settings(**values):
    return Settings(
        _env_file=None, ai_provider='fixture', embeddings_provider='fixture', **values
    )


def test_require_isolated_rejects_remote_targets_before_inspecting_containers():
    def inspect(names):
        raise AssertionError('containers must not be inspected for remote targets')

    for values in (
        {'database_url': 'postgresql://u@db.example.com/db'},
        {'neo4j_uri': 'neo4j+s://x.databases.neo4j.io'},
    ):
        with pytest.raises(IsolationError):
            require_isolated(settings(**values), inspect=inspect)


def test_require_isolated_wraps_owned_container_failures(monkeypatch):
    monkeypatch.setenv('COMPOSE_PROJECT_NAME', 'paa-eval')
    config = settings(
        database_url='postgresql://u@localhost:5432/db',
        neo4j_uri='bolt://127.0.0.1:7687',
    )

    def inspect(names):
        raise ValueError('cannot verify evaluation container identities')

    with pytest.raises(IsolationError, match='cannot verify'):
        require_isolated(config, inspect=inspect)
