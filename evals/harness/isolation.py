"""Isolation guard (closes gap A1): evaluation touches only fixture or loopback stores."""

from collections.abc import Callable
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


def check_postgres_dsn(dsn: str) -> None:
    """Accept loopback hosts or an explicit unix socket directory; reject all else."""
    try:
        params = conninfo_to_dict(dsn)
    except ProgrammingError:
        raise IsolationError('PostgreSQL DSN is not parseable') from None
    hosts = [
        h for key in ('host', 'hostaddr') for h in str(params.get(key, '')).split(',')
    ]
    hosts = [h for h in hosts if h]
    if not hosts:
        raise IsolationError(
            'PostgreSQL DSN has no explicit host; refusing to evaluate'
        )
    for host in hosts:
        if not (host.startswith('/') or _loopback(host)):
            raise IsolationError(
                f'PostgreSQL host {host!r} is not local; refusing to evaluate'
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
