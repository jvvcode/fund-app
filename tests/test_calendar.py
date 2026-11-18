from datetime import date

from fundapp.ingestion.calendar import is_trading_day


def test_known_trading_day():
    # A Tuesday, not a US market holiday.
    assert is_trading_day(date(2026, 1, 6))


def test_weekend_is_not_a_trading_day():
    assert not is_trading_day(date(2026, 1, 3))  # Saturday


def test_new_years_day_is_not_a_trading_day():
    assert not is_trading_day(date(2026, 1, 1))
