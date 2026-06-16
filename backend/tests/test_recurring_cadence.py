from datetime import date
from app.services.recurring_service import compute_next_run


def test_weekly_adds_seven_days():
    assert compute_next_run(date(2026, 6, 1), 'weekly') == date(2026, 6, 8)


def test_monthly_keeps_day_of_month():
    assert compute_next_run(date(2026, 6, 15), 'monthly') == date(2026, 7, 15)


def test_monthly_clamps_to_end_of_short_month():
    # Jan 31 -> Feb 28 (2026 is not a leap year)
    assert compute_next_run(date(2026, 1, 31), 'monthly') == date(2026, 2, 28)


def test_monthly_rolls_over_year():
    assert compute_next_run(date(2026, 12, 10), 'monthly') == date(2027, 1, 10)


def test_unknown_frequency_raises():
    import pytest
    with pytest.raises(ValueError):
        compute_next_run(date(2026, 6, 1), 'yearly')
