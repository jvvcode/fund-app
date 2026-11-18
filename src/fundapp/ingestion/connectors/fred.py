from __future__ import annotations

from datetime import date

from sqlalchemy import text

from fundapp.ingestion.base import Connector
from fundapp.utils.logging import get_logger

log = get_logger(__name__)

_SERIES = ["DGS10", "DGS2", "CPIAUCSL", "GDPC1"]  # yield curve, inflation, GDP growth

_UPSERT = text(
    """
    INSERT INTO macro_series (series_id, obs_date, value, unit, source)
    VALUES (:series_id, :obs_date, :value, :unit, 'FRED')
    ON CONFLICT (series_id, obs_date) DO UPDATE SET value = EXCLUDED.value
    """
)


class FredMacroConnector(Connector):
    """Weekly pull of rates and macro series. Free, low-cadence — deliberately
    not on the nightly critical path."""

    name = "fred"

    def fetch(self, as_of: date) -> list[dict]:
        # TODO: call FRED's API for each series in _SERIES.
        # Expected per-row shape: {"series_id": str, "value": Decimal, "unit": str}
        raise NotImplementedError("wire the FRED HTTP client here")

    def validate(self, rows: list[dict]) -> list[dict]:
        return [r for r in rows if r.get("value") is not None]

    def upsert(self, as_of: date, rows: list[dict]) -> None:
        from fundapp.store.engine import SessionLocal

        with SessionLocal() as s:
            for r in rows:
                s.execute(_UPSERT, {"obs_date": as_of, **r})
            s.commit()

    def run(self, as_of: date) -> None:
        raw = self.fetch(as_of)
        self.land_raw(as_of, raw)
        good = self.validate(raw)
        self.upsert(as_of, good)
        log.info("fred: %d series updated for %s", len(good), as_of)
