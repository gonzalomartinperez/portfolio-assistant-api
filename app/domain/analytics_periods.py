"""UTC calendar periods; accepted page views are not unique visitors."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

Period = Literal['day', 'week', 'month']


@dataclass(frozen=True)
class CalendarWindow:
    start: date
    end: date
    partial: bool


def calendar_window(now: datetime, period: Period, offset: int = 0) -> CalendarWindow:
    if now.tzinfo is None or type(offset) is not int or not 0 <= offset <= 2:
        raise ValueError('invalid_calendar_window')
    today = now.astimezone(UTC).date()
    if period == 'month':
        ordinal = today.year * 12 + today.month - 1 - offset
        year, month = divmod(ordinal, 12)
        next_year, next_month = divmod(ordinal + 1, 12)
        start = date(year, month + 1, 1)
        end = date(next_year, next_month + 1, 1)
    elif period == 'week':
        start = today - timedelta(days=today.weekday() + 7 * offset)
        end = start + timedelta(days=7)
    elif period == 'day':
        start = today - timedelta(days=offset)
        end = start + timedelta(days=1)
    else:
        raise ValueError('invalid_calendar_period')
    return CalendarWindow(start, end, start <= today < end)
