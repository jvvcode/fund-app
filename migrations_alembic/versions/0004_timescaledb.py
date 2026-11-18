"""enable timescaledb extension

PostgreSQL 17 + TimescaleDB is a locked architectural decision (see README).
db/migrations/0004_timescaledb.sql is the human-readable source this revision
executes verbatim. This only enables the extension — converting `prices` (or
any future time-series table) into a hypertable is a separate, deliberate
migration, added when the query-performance need is real rather than upfront.

Revision ID: 0004_timescaledb
Revises: 0003_transaction_corrections
Create Date: 2026-01-04
"""

from alembic import op

revision = "0004_timescaledb"
down_revision = "0003_transaction_corrections"
branch_labels = None
depends_on = None

_SQL = """
-- Enable the TimescaleDB extension (locked architectural decision: PostgreSQL 17
-- + TimescaleDB from day one). The `prices` table (0002_market_data.sql) is the
-- natural first hypertable candidate now that it exists, but converting it is a
-- deliberate follow-up, not automatic here — hypertable conversion changes query
-- planning and partitioning behavior and deserves its own reviewed migration.

CREATE EXTENSION IF NOT EXISTS timescaledb;

"""


def upgrade() -> None:
    op.execute(_SQL)


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE;")
