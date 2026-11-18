from decimal import Decimal

import pytest

from fundapp.ingestion.connectors.polygon import PolygonPriceConnector, _parse_bars


def test_validate_passes_through_good_rows():
    c = PolygonPriceConnector()
    rows = [{"security_id": 1, "close": 100.0}, {"security_id": 2, "close": 200.0}]
    good, bad = c.validate(rows)
    assert good == rows
    assert bad == []


def test_validate_halts_above_5pct_missing():
    c = PolygonPriceConnector()
    rows = [{"security_id": i, "close": None if i == 0 else 1.0} for i in range(10)]
    # 1/10 = 10% missing -> should raise
    with pytest.raises(RuntimeError):
        c.validate(rows)


def test_parse_bars_maps_matched_ticker_by_T_field():
    payload = {
        "status": "OK",
        "results": [
            {"T": "AAPL", "o": 149.5, "h": 152.0, "l": 149.0, "c": 151.2, "v": 1000000},
        ],
    }
    rows = _parse_bars(payload, {"AAPL": 1})
    assert rows == [
        {
            "security_id": 1,
            "open": Decimal("149.5"),
            "high": Decimal("152.0"),
            "low": Decimal("149.0"),
            "close": Decimal("151.2"),
            "volume": 1000000,
            "open_interest": None,
            "iv": None,
        }
    ]


def test_parse_bars_unmatched_ticker_becomes_missing_row():
    # No bar printed (halted, delisted, no trades that day) -> a row of Nones,
    # which validate() then counts against the missing-data threshold.
    payload = {"status": "OK", "results": []}
    rows = _parse_bars(payload, {"HALTED": 2})
    assert rows == [
        {
            "security_id": 2,
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
            "open_interest": None,
            "iv": None,
        }
    ]


def test_parse_bars_ignores_tickers_outside_universe():
    payload = {"status": "OK", "results": [{"T": "TSLA", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1}]}
    rows = _parse_bars(payload, {"AAPL": 1})  # TSLA isn't held, AAPL has no bar
    assert len(rows) == 1
    assert rows[0]["security_id"] == 1
    assert rows[0]["close"] is None
