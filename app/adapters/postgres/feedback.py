"""Current ratings on retained answers, without reading their content or IDs."""

from typing import TYPE_CHECKING

from app.application.feedback import FeedbackSummary

if TYPE_CHECKING:
    from app.adapters.postgres.db import Connect
    from app.application.clock import Clock


class PostgresFeedback:
    def __init__(self, connection: Connect, *, clock: Clock) -> None:
        self.clock = clock
        self.connection = connection

    def read(self) -> FeedbackSummary:
        with self.connection() as conn:
            conn.execute("SET LOCAL statement_timeout='1000ms'")
            row = conn.execute(
                "SELECT count(*) FILTER (WHERE f.rating='up') AS up,count(*) FILTER (WHERE f.rating='down') AS down FROM feedback f JOIN messages m ON m.id=f.message_id WHERE m.role='assistant' AND m.created_at>=now()-interval '7 days'"
            ).fetchone()
        return FeedbackSummary(self.clock.now().isoformat(), row["up"], row["down"])
