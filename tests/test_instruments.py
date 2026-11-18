from decimal import Decimal

import pytest

from fundapp.instruments import cash, derivatives  # noqa: F401  (register types)
from fundapp.instruments.base import Instrument


def test_linear_exposure_equals_market_value():
    eq = Instrument.from_type("equity", security_id=1, currency="USD")
    mv = eq.market_value(Decimal(10), Decimal(100))
    exp = eq.exposure(Decimal(10), Decimal(100))
    assert mv == exp == Decimal(1000)


def test_option_exposure_uses_underlying_and_delta():
    opt = Instrument.from_type(
        "option",
        security_id=2,
        currency="USD",
        contract_multiplier=Decimal(100),
        underlying_security_id=1,
        option_type="call",
        strike=Decimal(95),
    )
    # 1 contract, delta 0.5, underlying at 100, multiplier 100 -> 5000 exposure.
    exp = opt.exposure(Decimal(1), Decimal(3), delta=Decimal("0.5"), underlying_price=Decimal(100))
    assert exp == Decimal(5000)
    assert opt.is_derivative


def test_future_mv_zero_but_exposure_is_notional():
    fut = Instrument.from_type(
        "future",
        security_id=3,
        currency="USD",
        contract_multiplier=Decimal(50),
        underlying_security_id=1,
    )
    assert fut.market_value(Decimal(2), Decimal(4500)) == Decimal(0)
    assert fut.exposure(Decimal(2), Decimal(4500)) == Decimal(450000)


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        Instrument.from_type("banana", security_id=9, currency="USD")
