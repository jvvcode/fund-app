from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from .base import Instrument, register


@register("option")
@dataclass
class Option(Instrument):
    option_type: Optional[str] = None  # 'call' | 'put'
    strike: Optional[Decimal] = None
    expiry: Optional[date] = None

    def market_value(self, quantity: Decimal, price: Decimal, fx: Decimal = Decimal(1)) -> Decimal:
        # `price` is the option premium per unit.
        return quantity * price * self.contract_multiplier * fx

    def exposure(
        self,
        quantity: Decimal,
        price: Decimal,
        fx: Decimal = Decimal(1),
        delta: Decimal = Decimal(1),
        underlying_price: Optional[Decimal] = None,
    ) -> Decimal:
        if underlying_price is None:
            raise ValueError("underlying_price required for option exposure")
        return quantity * delta * underlying_price * self.contract_multiplier * fx


@register("future")
@dataclass
class Future(Instrument):
    expiry: Optional[date] = None

    def market_value(self, quantity: Decimal, price: Decimal, fx: Decimal = Decimal(1)) -> Decimal:
        # Futures settle daily; carried MV is ~0 (variation margin flows as cash).
        return Decimal(0)

    def exposure(
        self,
        quantity: Decimal,
        price: Decimal,
        fx: Decimal = Decimal(1),
        delta: Decimal = Decimal(1),
        underlying_price: Optional[Decimal] = None,
    ) -> Decimal:
        ref = underlying_price if underlying_price is not None else price
        return quantity * ref * self.contract_multiplier * fx


@register("forward")
@dataclass
class Forward(Instrument):
    expiry: Optional[date] = None
    notional: Optional[Decimal] = None

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
        ref = underlying_price if underlying_price is not None else price
        base = self.notional if self.notional is not None else quantity * ref * self.contract_multiplier
        return base * fx


@register("swap")
@dataclass
class Swap(Instrument):
    notional: Optional[Decimal] = None

    def market_value(self, quantity: Decimal, price: Decimal, fx: Decimal = Decimal(1)) -> Decimal:
        # Swap MtM requires a leg-level pricing model — deferred to Phase 3.
        raise NotImplementedError("Swap valuation model not implemented yet")

    def exposure(
        self,
        quantity: Decimal,
        price: Decimal,
        fx: Decimal = Decimal(1),
        delta: Decimal = Decimal(1),
        underlying_price: Optional[Decimal] = None,
    ) -> Decimal:
        if self.notional is None:
            raise ValueError("notional required for swap exposure")
        return self.notional * delta * fx
