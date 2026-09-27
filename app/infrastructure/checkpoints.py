"""Checkpoint storage and durable cleanup, separate from conversation transactions."""

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row

from app.bootstrap.config import settings
from app.infrastructure.db import connect


def delete_checkpoint(thread_id: str, database_url: str | None = None) -> None:
    """Delete one checkpoint with bounded connection and statement timeouts."""
    with psycopg.connect(
        database_url or settings().database_url,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
        connect_timeout=5,
        options='-c statement_timeout=5000',
    ) as conn:
        PostgresSaver(conn).delete_thread(thread_id)


def drain_cleanup(
    *, connection=connect, database_url: str | None = None, limit: int = 100
) -> int:
    """Retry at most 100 tombstones; retain recent ones against late checkpoint writes."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT thread_id FROM checkpoint_cleanup WHERE cleaned_at IS NULL OR created_at<now()-interval '10 minutes' ORDER BY created_at LIMIT %s",
            (limit,),
        ).fetchall()
    for row in rows:
        delete_checkpoint(row['thread_id'], database_url)
        with connection() as conn:
            conn.execute(
                'UPDATE checkpoint_cleanup SET cleaned_at=now() WHERE thread_id=%s',
                (row['thread_id'],),
            )
            conn.execute(
                "DELETE FROM checkpoint_cleanup WHERE thread_id=%s AND created_at<now()-interval '10 minutes'",
                (row['thread_id'],),
            )
    return len(rows)
