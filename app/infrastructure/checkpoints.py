"""Checkpoint storage and durable cleanup, separate from conversation transactions."""

from langgraph.checkpoint.postgres import PostgresSaver

from app.bootstrap.config import settings
from app.infrastructure.db import connect


def delete_checkpoint(thread_id: str) -> None:
    with PostgresSaver.from_conn_string(settings().database_url) as saver:
        saver.delete_thread(thread_id)


def drain_cleanup() -> int:
    with connect() as conn:
        rows = conn.execute(
            'SELECT thread_id FROM checkpoint_cleanup ORDER BY created_at LIMIT 100'
        ).fetchall()
    for row in rows:
        delete_checkpoint(row['thread_id'])
        with connect() as conn:
            conn.execute(
                "DELETE FROM checkpoint_cleanup WHERE thread_id=%s AND created_at<now()-interval '10 minutes'",
                (row['thread_id'],),
            )
    return len(rows)
