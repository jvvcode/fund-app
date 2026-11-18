from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, Optional

# Registry mapping instrument_type -> concrete Instrument subclass. Populated by
# the @register decorator so valuation/exposure logic dispatches by type.
_REGISTRY: dict[str, type["Instrument"]] = {}


def register(instrument_type: str):
    def deco(cls: type["Instrument"]) -> type["Instrument"]:
        cls.instrument_type = instrument_type
        _REGISTRY[instrument_type] = cls
        return cls

    return deco


def registry() -> dict[str, type["Instrument"]]:
    return dict(_REGISTRY)


@dataclass
class Instrument(ABC):
    # Common attributes drawn from a security_master row.
    security_id: int
    currency: str
    contract_multiplier: Decimal = Decimal(1)
    underlying_security_id: Optional[int] = None
    instrument_type: ClassVar[str] = "abstract"

    @property
    def is_derivative(self) -> bool:
        return self.underlying_security_id is not None

    # Mark-to-market value of a holding, in `currency` * fx.
    @abstractmethod
    def market_value(
        self, quantity: Decimal, price: Decimal, fx: Decimal = Decimal(1)
    ) -> Decimal: ...

    # Economic exposure to the underlying. Equals market value for linear
    # instruments; delta * underlying notional for derivatives.
    @abstractmethod
    def exposure(
        self,
        quantity: Decimal,
        price: Decimal,
        fx: Decimal = Decimal(1),
        delta: Decimal = Decimal(1),
        underlying_price: Optional[Decimal] = None,
    ) -> Decimal: ...

    @classmethod
    def from_type(cls, instrument_type: str, **kwargs) -> "Instrument":
        try:
            klass = _REGISTRY[instrument_type]
        except KeyError as exc:
            raise ValueError(f"Unknown instrument_type: {instrument_type!r}") from exc
        return klass(**kwargs)
