from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# A connection capability: calling it yields a context-managed dict-row connection.
type Connect = Callable[[], AbstractContextManager[Any]]


def pool(database_url: str) -> ConnectionPool:
    return ConnectionPool(
        database_url,
        open=False,
        min_size=1,
        max_size=8,
        timeout=5,
        max_waiting=16,
        kwargs={
            "row_factory": dict_row,
            "connect_timeout": 5,
            "options": "-c statement_timeout=10000 -c lock_timeout=5000",
        },
    )


@contextmanager
def connect(database_url: str) -> Iterator[Any]:
    # CLI operations own short-lived connections; the HTTP composition injects a pool.
    with psycopg.connect(
        database_url,
        row_factory=dict_row,
        connect_timeout=5,
        options="-c statement_timeout=10000 -c lock_timeout=5000",
    ) as conn:
        yield conn


def translated(connection: Connect) -> Connect:
    """Wrap a connection capability with a safe, application-owned failure type."""
    from psycopg_pool import PoolTimeout, TooManyRequests

    from app.domain.errors import DependencyUnavailableError

    @contextmanager
    def operation() -> Iterator[Any]:
        try:
            with connection() as conn:
                yield conn
        except psycopg.Error, PoolTimeout, TooManyRequests:
            raise DependencyUnavailableError("storage_unavailable") from None

    return operation
