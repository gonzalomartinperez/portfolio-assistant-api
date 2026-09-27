"""One transaction per operation; ownership predicates stay with the mutation."""

from contextlib import contextmanager
from dataclasses import fields
from uuid import uuid4

from psycopg.errors import UniqueViolation

from app.domain.conversations import Conversation, Message, Run, Session
from app.domain.errors import RejectedError


def record(model, row):
    return model(**{field.name: row[field.name] for field in fields(model)})


class PostgresConversations:
    def __init__(self, connect):
        self.connect = connect

    @contextmanager
    def owned(self, session_id, conversation_id):
        with self.connect() as conn:
            row = conn.execute(
                'SELECT id FROM conversations WHERE id=%s AND session_id=%s FOR UPDATE',
                (conversation_id, session_id),
            ).fetchone()
            if not row:
                raise RejectedError('not_found', 404)
            yield conn

    def session(self, secret_digest):
        with self.connect() as conn:
            row = conn.execute(
                'SELECT id,csrf_token,expires_at FROM sessions WHERE secret_digest=%s AND expires_at>now()',
                (secret_digest,),
            ).fetchone()
        return record(Session, row) if row else None

    def create_session(self, session_id, secret_digest, csrf, expires):
        with self.connect() as conn:
            conn.execute(
                'INSERT INTO sessions(id,secret_digest,csrf_token,expires_at) VALUES (%s,%s,%s,%s)',
                (session_id, secret_digest, csrf, expires),
            )

    def delete_session(self, session_id):
        with self.connect() as conn:
            conn.execute(
                'INSERT INTO checkpoint_cleanup(thread_id) SELECT r.id::text FROM runs r JOIN conversations c ON c.id=r.conversation_id WHERE c.session_id=%s ON CONFLICT DO NOTHING',
                (session_id,),
            )
            conn.execute('DELETE FROM sessions WHERE id=%s', (session_id,))

    def rate_limit(self, subject_hash, operation, limit):
        with self.connect() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(472018)')
            count = conn.execute(
                "SELECT count(*) AS n FROM rate_events WHERE subject_hash=%s AND operation=%s AND created_at>now()-interval '1 hour'",
                (subject_hash, operation),
            ).fetchone()['n']
            if count >= limit:
                raise RejectedError('rate_limited', 429)
            conn.execute(
                'INSERT INTO rate_events(id,subject_hash,operation) VALUES (%s,%s,%s)',
                (uuid4(), subject_hash, operation),
            )

    def create(self, session_id, title):
        with self.connect() as conn:
            # Serialize per-session allocation so the storage bound survives concurrent requests.
            conn.execute(
                'SELECT id FROM sessions WHERE id=%s FOR UPDATE', (session_id,)
            )
            count = conn.execute(
                'SELECT count(*) AS n FROM conversations WHERE session_id=%s',
                (session_id,),
            ).fetchone()['n']
            if count >= 100:
                raise RejectedError('conversation_limit', 429)
            row = conn.execute(
                'INSERT INTO conversations(id,session_id,title) VALUES (%s,%s,%s) RETURNING *',
                (uuid4(), session_id, title),
            ).fetchone()
        return record(Conversation, row)

    def list_conversations(self, session_id, limit, cursor):
        with self.connect() as conn:
            rows = conn.execute(
                'SELECT * FROM conversations WHERE session_id=%s AND (%s::timestamptz IS NULL OR updated_at<%s) ORDER BY updated_at DESC LIMIT %s',
                (session_id, cursor, cursor, limit),
            ).fetchall()
        return [record(Conversation, row) for row in rows]

    def rename(self, session_id, conversation_id, title):
        with self.owned(session_id, conversation_id) as conn:
            row = conn.execute(
                'UPDATE conversations SET title=%s,updated_at=now() WHERE id=%s RETURNING *',
                (title, conversation_id),
            ).fetchone()
        return record(Conversation, row)

    def delete(self, session_id, conversation_id):
        with self.owned(session_id, conversation_id) as conn:
            conn.execute(
                'INSERT INTO checkpoint_cleanup(thread_id) SELECT id::text FROM runs WHERE conversation_id=%s ON CONFLICT DO NOTHING',
                (conversation_id,),
            )
            conn.execute('DELETE FROM conversations WHERE id=%s', (conversation_id,))

    def messages(self, session_id, conversation_id, limit, cursor):
        with self.owned(session_id, conversation_id) as conn:
            rows = conn.execute(
                'SELECT * FROM messages WHERE conversation_id=%s AND (%s::timestamptz IS NULL OR created_at<%s) ORDER BY created_at DESC LIMIT %s',
                (conversation_id, cursor, cursor, limit),
            ).fetchall()
        return [record(Message, row) for row in rows]

    def prepare_run(self, session_id, conversation_id, content, payload_hash, key):
        with self.owned(session_id, conversation_id) as conn:
            conn.execute(
                "UPDATE runs SET state='interrupted',error_code='run_interrupted',updated_at=now() WHERE state IN ('pending','running') AND lease_until<now()"
            )
            existing = conn.execute(
                'SELECT * FROM runs WHERE conversation_id=%s AND idempotency_key=%s',
                (conversation_id, key),
            ).fetchone()
            if existing:
                raise RejectedError(
                    'idempotency_conflict'
                    if existing['payload_hash'] != payload_hash
                    else 'run_already_exists',
                    409,
                )
            conn.execute('SELECT pg_advisory_xact_lock(472020)')
            count = conn.execute(
                "SELECT count(*) AS n FROM runs WHERE state IN ('pending','running')"
            ).fetchone()['n']
            if count >= 4:
                raise RejectedError('busy', 429)
            history = conn.execute(
                'SELECT count(*) AS n FROM messages WHERE conversation_id=%s',
                (conversation_id,),
            ).fetchone()['n']
            if history >= 200:
                raise RejectedError('history_limit', 429)
            run_id = uuid4()
            try:
                conn.execute(
                    "INSERT INTO runs(id,conversation_id,idempotency_key,payload_hash,state,lease_until) VALUES (%s,%s,%s,%s,'pending',now()+interval '5 minutes')",
                    (run_id, conversation_id, key, payload_hash),
                )
                conn.execute(
                    "INSERT INTO messages(id,conversation_id,role,content) VALUES (%s,%s,'user',%s)",
                    (uuid4(), conversation_id, content),
                )
                conn.execute(
                    'UPDATE conversations SET updated_at=now() WHERE id=%s',
                    (conversation_id,),
                )
            except UniqueViolation:
                raise RejectedError('run_in_progress', 409) from None
        return run_id

    def run(self, session_id, run_id, cancel=False):
        with self.connect() as conn:
            conn.execute(
                "UPDATE runs SET state='interrupted',error_code='run_interrupted',updated_at=now() WHERE state IN ('pending','running') AND lease_until<now()"
            )
            if cancel:
                conn.execute(
                    "UPDATE runs r SET state='cancelled',lease_until=NULL,updated_at=now() FROM conversations c WHERE r.id=%s AND r.conversation_id=c.id AND c.session_id=%s AND r.state IN ('pending','running')",
                    (run_id, session_id),
                )
            row = conn.execute(
                'SELECT r.* FROM runs r JOIN conversations c ON c.id=r.conversation_id WHERE r.id=%s AND c.session_id=%s',
                (run_id, session_id),
            ).fetchone()
        if not row:
            raise RejectedError('not_found', 404)
        return record(Run, row)

    def feedback(self, session_id, message_id, rating):
        with self.connect() as conn:
            found = conn.execute(
                "SELECT m.id FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE m.id=%s AND c.session_id=%s AND m.role='assistant'",
                (message_id, session_id),
            ).fetchone()
            if not found:
                raise RejectedError('not_found', 404)
            conn.execute(
                'INSERT INTO feedback(message_id,session_id,rating) VALUES (%s,%s,%s) ON CONFLICT(message_id) DO UPDATE SET rating=excluded.rating',
                (message_id, session_id, rating),
            )
