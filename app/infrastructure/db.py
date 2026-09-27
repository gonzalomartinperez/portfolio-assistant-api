from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.bootstrap.config import settings


def pool(database_url: str) -> ConnectionPool:
    return ConnectionPool(
        database_url,
        open=False,
        min_size=1,
        max_size=8,
        timeout=5,
        max_waiting=16,
        kwargs={
            'row_factory': dict_row,
            'connect_timeout': 5,
            'options': '-c statement_timeout=10000 -c lock_timeout=5000',
        },
    )


@contextmanager
def connect():
    # CLI operations own short-lived connections; the HTTP composition injects a pool.
    with psycopg.connect(
        settings().database_url,
        row_factory=dict_row,
        connect_timeout=5,
        options='-c statement_timeout=10000 -c lock_timeout=5000',
    ) as conn:
        yield conn
