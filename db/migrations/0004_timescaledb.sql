-- Enable the TimescaleDB extension (locked architectural decision: PostgreSQL 17
-- + TimescaleDB from day one). The `prices` table (0002_market_data.sql) is the
-- natural first hypertable candidate now that it exists, but converting it is a
-- deliberate follow-up, not automatic here — hypertable conversion changes query
-- planning and partitioning behavior and deserves its own reviewed migration.

CREATE EXTENSION IF NOT EXISTS timescaledb;
