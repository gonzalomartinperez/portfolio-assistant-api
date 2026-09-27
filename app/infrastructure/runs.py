import asyncio
import json
from uuid import UUID, uuid4


class PostgresRuns:
    def __init__(self, connect):
        self.connect = connect

    async def start(self, run_id: UUID) -> bool:
        return await asyncio.to_thread(self._transition, run_id, 'running')

    async def running(self, run_id: UUID) -> bool:
        def read():
            with self.connect() as conn:
                row = conn.execute(
                    'SELECT state FROM runs WHERE id=%s', (run_id,)
                ).fetchone()
                return bool(row and row['state'] == 'running')

        return await asyncio.to_thread(read)

    def _transition(self, run_id, target, code=None):
        with self.connect() as conn:
            if target == 'running':
                return bool(
                    conn.execute(
                        "UPDATE runs SET state='running',lease_until=now()+interval '5 minutes',updated_at=now() WHERE id=%s AND state='pending' RETURNING id",
                        (run_id,),
                    ).fetchone()
                )
            return bool(
                conn.execute(
                    "UPDATE runs SET state=%s,error_code=%s,lease_until=NULL,updated_at=now() WHERE id=%s AND state IN ('pending','running') RETURNING id",
                    (target, code, run_id),
                ).fetchone()
            )

    async def complete(
        self,
        run_id: UUID,
        conversation_id: UUID,
        answer: str,
        citations: list[dict[str, object]],
    ) -> UUID | None:
        def save():
            with self.connect() as conn:
                state = conn.execute(
                    'SELECT state FROM runs WHERE id=%s FOR UPDATE', (run_id,)
                ).fetchone()
                if not state or state['state'] != 'running':
                    return None
                message_id = uuid4()
                conn.execute(
                    "INSERT INTO messages(id,conversation_id,role,content,citations) VALUES (%s,%s,'assistant',%s,%s)",
                    (message_id, conversation_id, answer, json.dumps(citations)),
                )
                conn.execute(
                    "UPDATE runs SET state='completed',message_id=%s,lease_until=NULL,updated_at=now() WHERE id=%s",
                    (message_id, run_id),
                )
                return message_id

        return await asyncio.to_thread(save)

    async def fail(self, run_id: UUID, code: str) -> bool:
        return await asyncio.to_thread(self._transition, run_id, 'failed', code)

    async def interrupt(self, run_id: UUID) -> None:
        await asyncio.to_thread(
            self._transition, run_id, 'interrupted', 'run_interrupted'
        )
