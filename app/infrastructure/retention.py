"""Prune expired anonymous data and its LangGraph checkpoints."""

from app.infrastructure.db import connect


def prune() -> dict[str, int]:
    with connect() as conn:
        run_ids = [
            str(row['id'])
            for row in conn.execute(
                'SELECT r.id FROM runs r JOIN conversations c ON c.id=r.conversation_id JOIN sessions s ON s.id=c.session_id WHERE s.expires_at<=now()'
            ).fetchall()
        ]
        for run_id in run_ids:
            conn.execute(
                'INSERT INTO checkpoint_cleanup(thread_id) VALUES (%s) ON CONFLICT DO NOTHING',
                (run_id,),
            )
        removed = conn.execute(
            'DELETE FROM sessions WHERE expires_at<=now() RETURNING id'
        ).fetchall()
        conn.execute("DELETE FROM rate_events WHERE created_at<now()-interval '2 days'")
    from app.infrastructure.checkpoints import drain_cleanup

    drain_cleanup()
    return {'sessions': len(removed), 'checkpoints': len(run_ids)}


if __name__ == '__main__':
    print(prune())
