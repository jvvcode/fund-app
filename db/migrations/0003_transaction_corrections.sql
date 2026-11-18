-- Support detecting broker corrections (same external_ref, different values),
-- not just true duplicates (same external_ref, same values). Corrections are
-- booked as a reversal + a new corrected entry, never an UPDATE — this column
-- links both back to the original broker reference for lookup and traceability.

ALTER TABLE transactions ADD COLUMN corrects_external_ref TEXT;
CREATE INDEX ix_txn_corrects_external_ref
    ON transactions(corrects_external_ref) WHERE corrects_external_ref IS NOT NULL;
