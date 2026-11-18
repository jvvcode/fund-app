from __future__ import annotations

from datetime import date

import pandas_market_calendars as mcal

_NYSE = mcal.get_calendar("NYSE")


def is_trading_day(d: date) -> bool:
    """Single shared trading-calendar check. Used by both the nightly
    scheduler and scripts/backfill_prices.py — a holiday or weekend must be
    skipped identically in both places, not re-implemented in each."""
    return not _NYSE.schedule(start_date=d, end_date=d).empty
