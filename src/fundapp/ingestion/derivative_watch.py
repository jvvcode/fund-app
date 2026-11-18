from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from fundapp.store.models import DerivativeTerms, Instrument


def expiring_soon(session: Session, days: int = 5) -> list[dict]:
    """Positions in derivative contracts expiring within `days`. Run nightly so
    expiry/exercise/assignment events are anticipated rather than discovered
    after the fact in a broker statement."""
    cutoff = date.today() + timedelta(days=days)
    rows = session.execute(
        select(Instrument.security_id, Instrument.primary_ticker, DerivativeTerms.expiry)
        .join(DerivativeTerms, DerivativeTerms.security_id == Instrument.security_id)
        .where(DerivativeTerms.expiry >= date.today(), DerivativeTerms.expiry <= cutoff)
    ).all()
    return [{"security_id": r[0], "ticker": r[1], "expiry": r[2]} for r in rows]
