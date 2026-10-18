"""Calendar boundaries are independent of machine timezone and rolling windows."""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.domain.analytics_periods import calendar_window


@pytest.mark.parametrize(
    ('instant', 'period', 'offset', 'start', 'end', 'partial'),
    [
        ('2026-10-18T00:00:00+00:00', 'day', 0, '2026-10-18', '2026-10-19', True),
        ('2026-10-18T00:00:00+00:00', 'day', 1, '2026-10-17', '2026-10-18', False),
        ('2027-01-01T13:00:00+00:00', 'week', 0, '2026-12-28', '2027-01-04', True),
        ('2027-01-04T00:00:00+00:00', 'week', 1, '2026-12-28', '2027-01-04', False),
        ('2028-03-01T00:00:00+00:00', 'month', 1, '2028-02-01', '2028-03-01', False),
        ('2027-01-31T23:59:59+00:00', 'month', 2, '2026-11-01', '2026-12-01', False),
        ('2027-01-01T00:00:00+00:00', 'month', 1, '2026-12-01', '2027-01-01', False),
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
