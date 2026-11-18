from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .base import Instrument, register


@dataclass
class LinearInstrument(Instrument):
    # Cash / linear instruments: exposure equals market value.
    def market_value(self, quantity: Decimal, price: Decimal, fx: Decimal = Decimal(1)) -> Decimal:
        return quantity * price * self.contract_multiplier * fx

    def exposure(
        self,
        quantity: Decimal,
        price: Decimal,
        fx: Decimal = Decimal(1),
        delta: Decimal = Decimal(1),
        underlying_price: Optional[Decimal] = None,
    ) -> Decimal:
        return self.market_value(quantity, price, fx)


@register("equity")
@dataclass
class Equity(LinearInstrument):
    pass


@register("etf")
@dataclass
class ETF(LinearInstrument):
    pass


@register("fund")
@dataclass
class Fund(LinearInstrument):
    pass


@register("bond")
@dataclass
class Bond(LinearInstrument):
    pass


@register("cash")
@dataclass
class Cash(LinearInstrument):
    pass
