"""Wall-clock port: the single source of "now" for application and adapter code."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime


class Clock(Protocol):
    """Source of the current wall-clock time."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC wall time."""
        ...
