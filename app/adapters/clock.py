"""System clock adapter: the only module in app/ that reads wall-clock time."""

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
