"""transaction corrections: corrects_external_ref

db/migrations/0003_transaction_corrections.sql is the human-readable source
this revision executes verbatim.

Revision ID: 0003_transaction_corrections
Revises: 0002_market_data
Create Date: 2026-01-03
"""

from alembic import op

revision = "0003_transaction_corrections"
down_revision = "0002_market_data"
branch_labels = None
depends_on = None

_SQL = """
-- Support detecting broker corrections (same external_ref, different values),
-- not just true duplicates (same external_ref, same values). Corrections are
-- booked as a reversal + a new corrected entry, never an UPDATE — this column
-- links both back to the original broker reference for lookup and traceability.

ALTER TABLE transactions ADD COLUMN corrects_external_ref TEXT;
CREATE INDEX ix_txn_corrects_external_ref
    ON transactions(corrects_external_ref) WHERE corrects_external_ref IS NOT NULL;

"""


def upgrade() -> None:
    op.execute(_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_txn_corrects_external_ref;
        ALTER TABLE transactions DROP COLUMN IF EXISTS corrects_external_ref;
        """
    )
