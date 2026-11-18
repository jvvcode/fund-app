"""One-off historical price load: python scripts/backfill_prices.py --start 2024-01-01 --end 2024-12-31"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from fundapp.ingestion.calendar import is_trading_day
from fundapp.ingestion.connectors.polygon import PolygonPriceConnector
from fundapp.utils.logging import get_logger

log = get_logger(__name__)


def _daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = p.parse_args()

    connector = PolygonPriceConnector()
    for d in _daterange(date.fromisoformat(args.start), date.fromisoformat(args.end)):
        # Non-trading days must be skipped here exactly as the nightly scheduler
        # skips them — otherwise a weekend/holiday returns zero bars, trips
        # validate()'s >5%-missing halt, and kills the whole backfill run.
        if not is_trading_day(d):
            continue
        connector.run(d)
        log.info("backfilled %s", d)


if __name__ == "__main__":
    main()
