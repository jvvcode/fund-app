from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from fundapp.store.engine import SessionLocal
from fundapp.store.models import DerivativeTerms, Instrument


def run() -> None:
    with SessionLocal() as s:
        # Safe to re-run: the ISIN is unique, so a second insert would fail.
        existing = s.scalar(select(Instrument).where(Instrument.isin == "US0378331005"))
        if existing is not None:
            print(f"Already seeded (AAPL id={existing.security_id}) - nothing to do.")
            return

        aapl = Instrument(
            instrument_type="equity",
            primary_ticker="AAPL",
            isin="US0378331005",
            name="Apple Inc.",
            asset_class="equity",
            currency="USD",
            exchange="XNAS",
            country="US",
            sector="Technology",
        )
        s.add(aapl)
        s.flush()

        opt = Instrument(
            instrument_type="option",
            primary_ticker="AAPL 250117C00200000",
            name="AAPL Jan-25 200 Call",
            asset_class="option",
            currency="USD",
            exchange="OPRA",
            contract_multiplier=Decimal(100),
            underlying_security_id=aapl.security_id,
        )
        s.add(opt)
        s.flush()

        s.add(
            DerivativeTerms(
                security_id=opt.security_id,
                option_type="call",
                strike=Decimal(200),
                expiry=date(2025, 1, 17),
                exercise_style="american",
                settlement_type="physical",
            )
        )
        s.commit()

        underlying = s.scalar(
            select(Instrument).where(Instrument.security_id == aapl.security_id)
        )
        print(f"Seeded {underlying.primary_ticker} (id={aapl.security_id}) and an option on it (id={opt.security_id}).")


if __name__ == "__main__":
    run()
