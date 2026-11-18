from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pandas as pd
from sqlalchemy import select, text

from fundapp.ingestion.base import Connector
from fundapp.store.engine import SessionLocal
from fundapp.store.models import Instrument
from fundapp.store.parquet import write_timeseries
from fundapp.utils.config import settings
from fundapp.utils.logging import get_logger

log = get_logger(__name__)

_UPSERT = text(
    """
    INSERT INTO prices (security_id, price_date, open, high, low, close, volume,
                         open_interest, iv, source)
    VALUES (:security_id, :price_date, :open, :high, :low, :close, :volume,
            :open_interest, :iv, 'polygon')
    ON CONFLICT (security_id, price_date) DO UPDATE SET
        open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
        close = EXCLUDED.close, volume = EXCLUDED.volume,
        open_interest = EXCLUDED.open_interest, iv = EXCLUDED.iv
    """
)


def _dec(x) -> Decimal | None:
    return Decimal(str(x)) if x is not None else None


def _parse_bars(payload: dict, universe: dict[str, int]) -> list[dict]:
    """Pure transform: the grouped-daily response + our ticker->security_id map
    -> one row per tracked security. Split out from fetch() so the mapping and
    missing-bar logic is unit-testable without a network call. A ticker with no
    bar in `results` (halted, delisted, no trades) becomes a row of Nones, which
    validate() then counts against the >5%-missing threshold."""
    bars_by_ticker = {b["T"]: b for b in payload.get("results", []) if "T" in b}
    rows = []
    for ticker, security_id in universe.items():
        bar = bars_by_ticker.get(ticker)
        rows.append(
            {
                "security_id": security_id,
                "open": _dec(bar.get("o")) if bar else None,
                "high": _dec(bar.get("h")) if bar else None,
                "low": _dec(bar.get("l")) if bar else None,
                "close": _dec(bar.get("c")) if bar else None,
                "volume": int(bar["v"]) if bar and bar.get("v") is not None else None,
                # Options-only fields. Grouped-daily covers equities/ETFs; options
                # aggregates need Massive's separate options-data subscription
                # (Phase 3 — already flagged in the cost & licensing appendix),
                # so these stay NULL until that connector is wired.
                "open_interest": None,
                "iv": None,
            }
        )
    return rows


class PolygonPriceConnector(Connector):
    """Daily OHLCV for every active equity/ETF/fund, via Massive's (formerly
    Polygon.io's) grouped-daily endpoint — one HTTP call for the whole market,
    not one per security. At family-fund scale this also sidesteps rate limits
    entirely: it's the same single request whether the universe is 5 tickers
    or 500. The SAME `prices` row shape covers equities (open_interest/iv left
    NULL) and options (populated, once that connector exists) — one table, no
    derivative-specific branch downstream."""

    name = "polygon"

    def _active_universe(self) -> dict[str, int]:
        """Tickers this endpoint can actually price: equities, ETFs, funds.
        Bonds don't trade here; options/futures need a different endpoint and
        subscription (see _parse_bars)."""
        with SessionLocal() as s:
            rows = s.execute(
                select(Instrument.primary_ticker, Instrument.security_id).where(
                    Instrument.is_active.is_(True),
                    Instrument.instrument_type.in_(("equity", "etf", "fund")),
                    Instrument.primary_ticker.is_not(None),
                )
            ).all()
        return {ticker: security_id for ticker, security_id in rows}

    def fetch(self, as_of: date) -> list[dict]:
        universe = self._active_universe()
        if not universe:
            log.warning("no active equities/ETFs/funds in security_master — nothing to fetch")
            return []

        url = f"{settings.polygon_base_url}/v2/aggs/grouped/locale/us/market/stocks/{as_of.isoformat()}"
        resp = httpx.get(
            url,
            params={"adjusted": "true"},
            headers={"Authorization": f"Bearer {settings.polygon_api_key}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        payload = resp.json()

        if payload.get("status") not in ("OK", "DELAYED"):
            raise RuntimeError(f"Massive/Polygon returned status={payload.get('status')!r}: {payload}")

        return _parse_bars(payload, universe)

    def validate(self, rows: list[dict]) -> tuple[list[dict], list[dict]]:
        good = [r for r in rows if r.get("close") is not None]
        bad = [r for r in rows if r.get("close") is None]
        missing_pct = len(bad) / max(len(rows), 1)
        if missing_pct > 0.05:
            raise RuntimeError(
                f"{missing_pct:.1%} of securities missing a close price — halting, check feed"
            )
        return good, bad

    def upsert(self, as_of: date, rows: list[dict]) -> None:
        if not rows:
            return
        with SessionLocal() as s:
            for r in rows:
                s.execute(_UPSERT, {"price_date": as_of, **r})
            s.commit()
        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = as_of.isoformat()
            write_timeseries("prices", df)

    def run(self, as_of: date) -> None:
        raw = self.fetch(as_of)
        self.land_raw(as_of, raw)
        good, bad = self.validate(raw)
        if bad:
            log.warning("%d securities skipped (missing price) on %s", len(bad), as_of)
        self.upsert(as_of, good)
        log.info("polygon: %d prices upserted for %s", len(good), as_of)
