from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# NOTE: db/migrations/0001_initial.sql is the source of truth. These ORM models
# mirror it for application use. Enum columns use the Postgres ENUM types the
# migrations create (create_type=False: Alembic owns the schema, not the ORM).


class Base(DeclarativeBase):
    pass


class Instrument(Base):
    __tablename__ = "security_master"

    security_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_type: Mapped[str] = mapped_column(
        ENUM(
            "equity",
            "etf",
            "fund",
            "bond",
            "cash",
            "option",
            "future",
            "forward",
            "swap",
            name="instrument_type",
            create_type=False,
        )
    )
    primary_ticker: Mapped[str | None] = mapped_column(String(48))
    isin: Mapped[str | None] = mapped_column(CHAR(12))
    figi: Mapped[str | None] = mapped_column(CHAR(12))
    cusip: Mapped[str | None] = mapped_column(CHAR(9))
    name: Mapped[str | None] = mapped_column(Text)
    asset_class: Mapped[str | None] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(CHAR(3))
    exchange: Mapped[str | None] = mapped_column(String(16))
    country: Mapped[str | None] = mapped_column(CHAR(2))
    sector: Mapped[str | None] = mapped_column(String(64))
    benchmark_security_id: Mapped[int | None] = mapped_column(
        ForeignKey("security_master.security_id")
    )
    underlying_security_id: Mapped[int | None] = mapped_column(
        ForeignKey("security_master.security_id")
    )
    contract_multiplier: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    underlying = relationship(
        "Instrument", remote_side=[security_id], foreign_keys=[underlying_security_id]
    )
    terms = relationship("DerivativeTerms", back_populates="instrument", uselist=False)


class DerivativeTerms(Base):
    __tablename__ = "derivative_terms"

    security_id: Mapped[int] = mapped_column(
        ForeignKey("security_master.security_id"), primary_key=True
    )
    option_type: Mapped[str | None] = mapped_column(
        ENUM("call", "put", name="option_type", create_type=False)
    )
    strike: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    expiry: Mapped[date | None] = mapped_column(Date)
    exercise_style: Mapped[str | None] = mapped_column(
        ENUM("american", "european", name="exercise_style", create_type=False)
    )
    settlement_type: Mapped[str | None] = mapped_column(
        ENUM("physical", "cash", name="settlement_type", create_type=False)
    )
    tick_size: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    tick_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    notional: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    terms: Mapped[dict | None] = mapped_column(JSONB)

    instrument = relationship("Instrument", back_populates="terms")


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.account_id"))
    name: Mapped[str] = mapped_column(Text)
    custodian: Mapped[str | None] = mapped_column(Text)
    base_currency: Mapped[str] = mapped_column(CHAR(3), default="USD")
    benchmark_id: Mapped[int | None] = mapped_column(ForeignKey("benchmarks.benchmark_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Price(Base):
    # Hot window only (recent history). Full series lives in Parquet — see
    # store/parquet.py. open_interest / iv are populated for derivatives only.
    __tablename__ = "prices"

    security_id: Mapped[int] = mapped_column(
        ForeignKey("security_master.security_id"), primary_key=True
    )
    price_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    open_interest: Mapped[int | None] = mapped_column(BigInteger)
    iv: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    source: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MacroSeries(Base):
    __tablename__ = "macro_series"

    series_id: Mapped[str] = mapped_column(Text, primary_key=True)
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    unit: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, default="FRED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Benchmark(Base):
    __tablename__ = "benchmarks"

    benchmark_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text)
    security_id: Mapped[int | None] = mapped_column(ForeignKey("security_master.security_id"))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    txn_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"))
    security_id: Mapped[int | None] = mapped_column(ForeignKey("security_master.security_id"))
    txn_type: Mapped[str] = mapped_column(
        ENUM(
            "buy",
            "sell",
            "dividend",
            "interest",
            "fee",
            "deposit",
            "withdrawal",
            "corp_action",
            "premium",
            "exercise",
            "assignment",
            "expiry",
            "roll",
            "variation_margin",
            "margin_post",
            name="txn_type",
            create_type=False,
        )
    )
    trade_date: Mapped[date] = mapped_column(Date)
    settle_date: Mapped[date | None] = mapped_column(Date)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    currency: Mapped[str | None] = mapped_column(CHAR(3))
    fees: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    related_txn_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.txn_id"))
    external_ref: Mapped[str | None] = mapped_column(Text)
    corrects_external_ref: Mapped[str | None] = mapped_column(Text)
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaxLot(Base):
    __tablename__ = "tax_lots"

    lot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"))
    security_id: Mapped[int] = mapped_column(ForeignKey("security_master.security_id"))
    open_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    method: Mapped[str] = mapped_column(String(12), default="FIFO")
