"""System clock adapter: the only module in app/ that reads wall-clock time."""

from datetime import UTC, datetime


class SystemClock:
    """Clock adapter backed by the operating system wall clock."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC wall time."""
        return datetime.now(UTC)
