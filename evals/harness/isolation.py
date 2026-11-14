"""Isolation guard (closes gap A1): evaluation touches only fixture or loopback stores."""

import os
from collections.abc import Callable, Mapping
from urllib.parse import urlparse

from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict

from app.bootstrap.config import Settings
from scripts.evaluation_isolation import (
    LOOPBACK_HOSTS,
    EvaluationContainer,
    inspect_containers,
    validate_targets,
)


class IsolationError(ValueError):
    """The evaluation target is not an owned local fixture."""


def _loopback(host: str) -> bool:
    return host.strip('[]').lower() in LOOPBACK_HOSTS


def check_postgres_dsn(dsn: str, environ: Mapping[str, str] | None = None) -> None:
    """Accept only explicit loopback hosts.

    Unix sockets are rejected: ``validate_targets`` needs a loopback host and a
    published container port, so accepting them here would be inconsistent. libpq lets
    ``PGHOSTADDR`` override the connect address, so a non-loopback ``PGHOST`` or
    ``PGHOSTADDR`` in the environment is rejected too.
    """
    try:
        params = conninfo_to_dict(dsn)
    except ProgrammingError:
        raise IsolationError('PostgreSQL DSN is not parseable') from None
    env = os.environ if environ is None else environ
    for name in ('PGHOST', 'PGHOSTADDR'):
        for host in env.get(name, '').split(','):
            if host and not _loopback(host):
                raise IsolationError(f'{name} points at a non-local host; refusing')
    hosts = [
        h for key in ('host', 'hostaddr') for h in str(params.get(key, '')).split(',')
    ]
    hosts = [h for h in hosts if h]
    if not hosts:
        raise IsolationError(
            'PostgreSQL DSN has no explicit host; refusing to evaluate'
        )
    for host in hosts:
        if not _loopback(host):
            raise IsolationError(
                f'PostgreSQL host {host!r} is not a loopback host; refusing to evaluate'
            )


def check_neo4j_uri(uri: str) -> None:
    """Accept only loopback Neo4j hosts (any scheme or port)."""
    try:
        host = urlparse(uri).hostname
    except ValueError:
        host = None
    if host is None or not _loopback(host):
        raise IsolationError(f'Neo4j host {host!r} is not local; refusing to evaluate')


def require_isolated(
    config: Settings,
    *,
    inspect: Callable[
        [tuple[str, str]], list[EvaluationContainer]
    ] = inspect_containers,
) -> None:
    """Pure host checks first, then the owned-container identity checks."""
    check_postgres_dsn(config.database_url)
    check_neo4j_uri(config.neo4j_uri)
    try:
        validate_targets(config, inspect=inspect)
    except ValueError as error:
        raise IsolationError(str(error)) from None
