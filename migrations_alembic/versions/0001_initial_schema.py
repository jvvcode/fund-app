"""initial schema: security master, derivatives, ledger, positions

db/migrations/0001_initial.sql is the human-readable source of truth this
revision executes verbatim, so the schema is reviewable as plain SQL and
versioned by Alembic at the same time.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-01-01
"""

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

_SQL = """
-- Phase 1 initial schema: core data store (relational tier).
-- Time series live in Parquet, not here (see src/fundapp/store/parquet.py).
-- Derivative-ready from day one: instrument_type discriminator, self-referential
-- underlying, contract multiplier, and a derivative_terms extension table.

CREATE TYPE instrument_type AS ENUM
  ('equity','etf','fund','bond','cash','option','future','forward','swap');
CREATE TYPE option_type     AS ENUM ('call','put');
CREATE TYPE exercise_style  AS ENUM ('american','european');
CREATE TYPE settlement_type AS ENUM ('physical','cash');
CREATE TYPE txn_type AS ENUM
  ('buy','sell','dividend','interest','fee','deposit','withdrawal','corp_action',
   'premium','exercise','assignment','expiry','roll','variation_margin','margin_post');

-- ---------------------------------------------------------------------------
-- Security master: one row per instrument, cash or derivative.
-- ---------------------------------------------------------------------------
CREATE TABLE security_master (
    security_id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrument_type        instrument_type NOT NULL,
    primary_ticker         TEXT,
    isin                   CHAR(12),
    figi                   CHAR(12),
    cusip                  CHAR(9),
    name                   TEXT,
    asset_class            TEXT,
    currency               CHAR(3) NOT NULL,
    exchange               TEXT,
    country                CHAR(2),
    sector                 TEXT,
    benchmark_security_id  BIGINT REFERENCES security_master(security_id),
    underlying_security_id BIGINT REFERENCES security_master(security_id),
    contract_multiplier    NUMERIC(18,6),
    is_active              BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Derivatives must reference an underlying and carry a multiplier.
    CONSTRAINT chk_derivative_fields CHECK (
        (instrument_type IN ('option','future','forward','swap')
             AND underlying_security_id IS NOT NULL
             AND contract_multiplier   IS NOT NULL)
        OR
        (instrument_type NOT IN ('option','future','forward','swap'))
    ),
    -- An instrument cannot be its own underlying.
    CONSTRAINT chk_underlying_not_self CHECK (underlying_security_id <> security_id)
);
CREATE UNIQUE INDEX uq_security_isin ON security_master(isin) WHERE isin IS NOT NULL;
CREATE UNIQUE INDEX uq_security_figi ON security_master(figi) WHERE figi IS NOT NULL;
CREATE INDEX ix_security_underlying ON security_master(underlying_security_id);
CREATE INDEX ix_security_type       ON security_master(instrument_type);

-- ---------------------------------------------------------------------------
-- Derivative terms: 1:1 extension of security_master for derivative rows.
-- ---------------------------------------------------------------------------
CREATE TABLE derivative_terms (
    security_id     BIGINT PRIMARY KEY REFERENCES security_master(security_id) ON DELETE CASCADE,
    option_type     option_type,
    strike          NUMERIC(18,6),
    expiry          DATE,
    exercise_style  exercise_style,
    settlement_type settlement_type,
    tick_size       NUMERIC(18,8),
    tick_value      NUMERIC(18,6),
    notional        NUMERIC(20,4),
    terms           JSONB        -- long tail: swap legs, reset schedules, etc.
);

-- ---------------------------------------------------------------------------
-- Accounts: household -> portfolio -> account hierarchy.
-- ---------------------------------------------------------------------------
CREATE TABLE accounts (
    account_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_account_id BIGINT REFERENCES accounts(account_id),
    name              TEXT NOT NULL,
    custodian         TEXT,
    base_currency     CHAR(3) NOT NULL DEFAULT 'USD',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Transactions: append-only ledger, the source of truth.
-- Corrections are reversing entries (related_txn_id), never UPDATE/DELETE.
-- ---------------------------------------------------------------------------
CREATE TABLE transactions (
    txn_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id     BIGINT NOT NULL REFERENCES accounts(account_id),
    security_id    BIGINT REFERENCES security_master(security_id),
    txn_type       txn_type NOT NULL,
    trade_date     DATE NOT NULL,
    settle_date    DATE,
    quantity       NUMERIC(24,8),   -- signed: + long, - short/sell
    price          NUMERIC(18,6),
    amount         NUMERIC(20,4),   -- signed cash impact, in `currency`
    currency       CHAR(3),
    fees           NUMERIC(18,6) DEFAULT 0,
    related_txn_id BIGINT REFERENCES transactions(txn_id),
    external_ref   TEXT,
    known_at       TIMESTAMPTZ NOT NULL DEFAULT now(),  -- point-in-time: when we learned of it
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_txn_account_date ON transactions(account_id, trade_date);
CREATE INDEX ix_txn_security     ON transactions(security_id);
-- Enables idempotent re-import: ON CONFLICT (external_ref) ... DO NOTHING in broker.py.
CREATE UNIQUE INDEX uq_txn_external_ref ON transactions(external_ref) WHERE external_ref IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Tax lots: lot-level cost basis (enables specific-ID / FIFO harvesting).
-- ---------------------------------------------------------------------------
CREATE TABLE tax_lots (
    lot_id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id         BIGINT NOT NULL REFERENCES accounts(account_id),
    security_id        BIGINT NOT NULL REFERENCES security_master(security_id),
    open_date          DATE NOT NULL,
    quantity           NUMERIC(24,8) NOT NULL,
    cost_basis         NUMERIC(20,4) NOT NULL,
    remaining_quantity NUMERIC(24,8) NOT NULL,
    method             TEXT NOT NULL DEFAULT 'FIFO'
);
CREATE INDEX ix_lots_acct_sec ON tax_lots(account_id, security_id);

-- ---------------------------------------------------------------------------
-- Positions snapshot: DERIVED from transactions; rebuildable at any as_of.
-- Kept as a table for fast reads; transactions remain the source of truth.
-- market_value != exposure for derivatives (see exposure column).
-- ---------------------------------------------------------------------------
CREATE TABLE positions (
    account_id   BIGINT NOT NULL REFERENCES accounts(account_id),
    security_id  BIGINT NOT NULL REFERENCES security_master(security_id),
    as_of        DATE   NOT NULL,
    quantity     NUMERIC(24,8) NOT NULL,   -- signed
    avg_cost     NUMERIC(20,6),
    market_value NUMERIC(20,4),
    exposure     NUMERIC(24,4),            -- economic exposure to the underlying
    currency     CHAR(3),
    PRIMARY KEY (account_id, security_id, as_of)
);

"""


def upgrade() -> None:
    op.execute(_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS tax_lots, positions, transactions, accounts,
            derivative_terms, security_master CASCADE;
        DROP TYPE IF EXISTS txn_type, settlement_type, exercise_style,
            option_type, instrument_type;
        """
    )
