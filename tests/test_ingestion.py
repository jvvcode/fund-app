from datetime import date
from decimal import Decimal

import pytest

from fundapp.ingestion.connectors.broker import parse_occ_symbol


def test_parse_occ_symbol(sample_occ_symbol):
    parsed = parse_occ_symbol(sample_occ_symbol)
    assert parsed["underlying_ticker"] == "AAPL"
    assert parsed["option_type"] == "call"
    assert parsed["strike"] == Decimal("200")
    assert parsed["expiry"] == date(2025, 1, 17)


def test_parse_occ_symbol_put():
    parsed = parse_occ_symbol("SPY241220P00450000")
    assert parsed["option_type"] == "put"
    assert parsed["strike"] == Decimal("450")


def test_parse_occ_symbol_invalid():
    with pytest.raises(ValueError):
        parse_occ_symbol("NOT-A-SYMBOL")
