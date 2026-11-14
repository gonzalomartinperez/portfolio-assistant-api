"""Calendar boundaries are independent of machine timezone and rolling windows."""

import json
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.domain.analytics_periods import calendar_window


@pytest.mark.parametrize(
    ('instant', 'period', 'offset', 'start', 'end', 'partial'),
    [
        (
            row['instant'],
            row['period'],
            row['offset'],
            row['start'],
            row['end'],
            row['partial'],
        )
        for row in json.loads(
            Path('contracts/analytics-semantics.examples.json').read_text()
        )['periods']
    ],
)
def test_calendar_uses_half_open_utc_periods(
    instant, period, offset, start, end, partial
):
    window = calendar_window(datetime.fromisoformat(instant), period, offset)
    assert window.start == date.fromisoformat(start)
    assert window.end == date.fromisoformat(end)
    assert window.partial is partial


def test_calendar_normalizes_aware_inputs_and_rejects_ambiguous_naive_time():
    instant = datetime(2026, 12, 31, 21, tzinfo=timezone(-timedelta(hours=4)))
    assert calendar_window(instant, 'day').start == date(2027, 1, 1)
    with pytest.raises(ValueError):
        calendar_window(datetime(2026, 10, 18), 'day')


@pytest.mark.parametrize('offset', [-1, 3, True])
def test_period_offsets_are_bounded(offset):
    with pytest.raises(ValueError):
        calendar_window(datetime(2026, 10, 18, tzinfo=UTC), 'month', offset)
