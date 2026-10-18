"""Prune expired anonymous data and its LangGraph checkpoints."""

from app.adapters.postgres.analytics import prune_product_counts


def prune(*, connection, cleanup) -> dict[str, int]:
    with connection() as conn:
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
        conn.execute(
            "DELETE FROM operational_executions WHERE started_at<now()-interval '30 days'"
        )
        conn.execute(
            "UPDATE operational_executions SET stages='[]'::jsonb,sampled=false WHERE started_at<now()-interval '7 days' AND (sampled OR stages<>'[]'::jsonb)"
        )
        conn.execute(
            "DELETE FROM product_event_dedupe WHERE received_at<now()-interval '1 day'"
        )
        prune_product_counts(conn)
        removed = conn.execute(
            'DELETE FROM sessions WHERE expires_at<=now() RETURNING id'
        ).fetchall()
        conn.execute("DELETE FROM rate_events WHERE created_at<now()-interval '2 days'")
    cleanup()
    return {'sessions': len(removed), 'checkpoints': len(run_ids)}
