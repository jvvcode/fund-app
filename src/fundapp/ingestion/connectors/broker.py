from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from fundapp.ingestion.base import Connector
from fundapp.store.engine import SessionLocal
from fundapp.store.models import DerivativeTerms, Instrument, Transaction
from fundapp.utils.logging import get_logger

log = get_logger(__name__)

# OCC option symbol, e.g. "AAPL  250117C00200000" -> root + YYMMDD + C/P + strike*1000 (8 digits).
_OCC_RE = re.compile(
    r"^(?P<root>[A-Z]{1,6})(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})(?P<cp>[CP])(?P<strike>\d{8})$"
)

# external_ref is the broker's own transaction ID. The partial unique index on
# transactions.external_ref (0001_initial.sql) still backstops true duplicates at
# the DB level, but distinguishing "same row re-sent" from "broker corrected this
# trade" needs comparison logic no single INSERT can express — see
# _upsert_transaction below.

_ECON_FIELDS = ("security_id", "txn_type", "trade_date", "quantity", "price", "amount", "currency")


def _dec_eq(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return Decimal(a) == Decimal(str(b))


def _values_match(existing: Transaction, row: dict) -> bool:
    """Same economic content, not just the same external_ref."""
    return (
        existing.security_id == row.get("security_id")
        and existing.txn_type == row.get("txn_type")
        and existing.trade_date == row.get("trade_date")
        and _dec_eq(existing.quantity, row.get("quantity"))
        and _dec_eq(existing.price, row.get("price"))
        and _dec_eq(existing.amount, row.get("amount"))
        and (existing.currency or None) == (row.get("currency") or None)
    )


_TXN_CODE_MAP = {
    "BOT": "buy",
    "SLD": "sell",
    "DIV": "dividend",
    "INT": "interest",
    "FEE": "fee",
    "EXP": "expiry",
    "EXER": "exercise",
    "ASSN": "assignment",
    "ROLL": "roll",
    "VM": "variation_margin",
    "MARGIN": "margin_post",
}


def parse_occ_symbol(symbol: str) -> dict:
    """Decode an OCC-format option symbol into its underlying ticker, expiry,
    option type and strike — the derivative-specific step a broker import needs
    that a cash-instrument import doesn't."""
    m = _OCC_RE.match(symbol.replace(" ", "").upper())
    if not m:
        raise ValueError(f"not an OCC option symbol: {symbol!r}")
    year = 2000 + int(m["yy"])
    return {
        "underlying_ticker": m["root"],
        "expiry": date(year, int(m["mm"]), int(m["dd"])),
        "option_type": "call" if m["cp"] == "C" else "put",
        "strike": Decimal(m["strike"]) / Decimal(1000),
    }


class BrokerImportConnector(Connector):
    """Imports positions & transactions from a broker statement (CSV/API).
    Cash instruments resolve directly by ticker/ISIN against security_master.
    Derivative symbols are parsed (parse_occ_symbol) and, if not yet known,
    a security_master row is created on the fly — underlying_security_id and
    contract_multiplier populated — so nothing downstream special-cases them."""

    name = "broker"

    def fetch(self, as_of: date) -> list[dict]:
        # TODO: pull today's statement rows from the broker API.
        # Expected per-row shape: {"symbol": str, "txn_code": str, "quantity": Decimal,
        #  "price": Decimal, "amount": Decimal, "currency": str, "trade_date": date}
        raise NotImplementedError("wire the broker API client here")

    def _resolve_security_id(self, session, symbol: str) -> int:
        occ = None
        try:
            occ = parse_occ_symbol(symbol)
        except ValueError:
            pass

        if occ is None:
            # Cash instrument: resolve by ticker (fallback path — prefer ISIN/FIGI
            # via fundapp.instruments.identifiers where available).
            row = session.scalar(select(Instrument).where(Instrument.primary_ticker == symbol))
            if row is None:
                raise LookupError(f"unresolved ticker: {symbol!r} — seed security_master first")
            return row.security_id

        row = session.scalar(select(Instrument).where(Instrument.primary_ticker == symbol))
        if row is not None:
            return row.security_id

        underlying = session.scalar(
            select(Instrument).where(Instrument.primary_ticker == occ["underlying_ticker"])
        )
        if underlying is None:
            raise LookupError(
                f"underlying {occ['underlying_ticker']!r} not in security_master — seed it first"
            )

        opt = Instrument(
            instrument_type="option",
            primary_ticker=symbol,
            currency=underlying.currency,
            contract_multiplier=Decimal(100),
            underlying_security_id=underlying.security_id,
        )
        session.add(opt)
        session.flush()
        session.add(
            DerivativeTerms(
                security_id=opt.security_id,
                option_type=occ["option_type"],
                strike=occ["strike"],
                expiry=occ["expiry"],
                exercise_style="american",
                settlement_type="physical",
            )
        )
        return opt.security_id

    def _reversal_of(self, existing: Transaction) -> dict:
        """A reversing entry for what's actually on file — not the incoming row,
        which may itself be wrong in ways beyond quantity/amount. Only quantity
        and amount flip sign; the trade itself (security, type, date, price) is
        restated as-is so the reversal is legible next to the original."""
        return {
            "account_id": existing.account_id,
            "security_id": existing.security_id,
            "txn_type": existing.txn_type,
            "trade_date": existing.trade_date,
            "quantity": -existing.quantity if existing.quantity is not None else None,
            "price": existing.price,
            "amount": -existing.amount if existing.amount is not None else None,
            "currency": existing.currency,
        }

    def _upsert_transaction(self, session, row: dict) -> None:
        ext_ref = row.get("external_ref")

        if not ext_ref:
            # Can't dedupe or detect corrections without a stable broker reference.
            session.add(Transaction(**row))
            log.warning(
                "no external_ref for security_id=%s on %s — cannot dedupe or detect "
                "corrections for this row",
                row.get("security_id"),
                row.get("trade_date"),
            )
            return

        existing = session.scalar(select(Transaction).where(Transaction.external_ref == ext_ref))
        if existing is None:
            # New reference. The partial unique index is the backstop if two runs
            # somehow race on this exact insert — that should raise, not swallow.
            session.add(Transaction(**row))
            return

        if _values_match(existing, row):
            log.debug("duplicate transaction skipped: external_ref=%s", ext_ref)
            return

        # Values differ from what's on file. Has this exact correction already
        # been booked? (Re-importing the same corrected statement must be a no-op.)
        prior_corrections = session.scalars(
            select(Transaction).where(Transaction.corrects_external_ref == ext_ref)
        ).all()
        for correction in prior_corrections:
            if _values_match(correction, row):
                log.debug("correction already applied for external_ref=%s", ext_ref)
                return

        if prior_corrections:
            # A correction is already on file and this incoming row matches
            # neither the original nor it — a second, distinct amendment.
            # Auto-booking another reversal here risks reversing a row that's
            # already superseded. Flag loudly; don't guess at the ledger.
            log.error(
                "second distinct correction for external_ref=%s — a correction is already "
                "on file and these values match neither the original nor it. Skipping "
                "automatic booking; enter this correction manually.",
                ext_ref,
            )
            return

        log.warning(
            "correction detected for external_ref=%s — booking reversal of txn %s + "
            "corrected entry",
            ext_ref,
            existing.txn_id,
        )
        session.add(
            Transaction(
                **self._reversal_of(existing),
                related_txn_id=existing.txn_id,
                corrects_external_ref=ext_ref,
            )
        )
        corrected = dict(row)
        corrected["external_ref"] = None  # only the original keeps the literal broker ref
        session.add(
            Transaction(**corrected, related_txn_id=existing.txn_id, corrects_external_ref=ext_ref)
        )

    def run(self, as_of: date) -> None:
        rows = self.fetch(as_of)
        self.land_raw(as_of, rows)
        with SessionLocal() as s:
            n = 0
            for r in rows:
                security_id = self._resolve_security_id(s, r["symbol"])
                self._upsert_transaction(
                    s,
                    {
                        "account_id": r["account_id"],
                        "security_id": security_id,
                        "txn_type": _TXN_CODE_MAP.get(r["txn_code"], "buy"),
                        "trade_date": r["trade_date"],
                        "quantity": r.get("quantity"),
                        "price": r.get("price"),
                        "amount": r.get("amount"),
                        "currency": r.get("currency"),
                        "external_ref": r.get("external_ref"),
                    },
                )
                n += 1
            s.commit()
        log.info(
            "broker: %d row(s) processed for %s (duplicates skipped, corrections detected)",
            n,
            as_of,
        )
