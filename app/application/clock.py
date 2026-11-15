"""Wall-clock port: the single source of "now" for application and adapter code."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware UTC wall time."""
        ...
