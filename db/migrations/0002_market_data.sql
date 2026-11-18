-- Phase 1 extension: market-data and benchmark tables.
-- `prices` is a hot Postgres window (recent history only, trimmed nightly) —
-- full history lives in Parquet via src/fundapp/store/parquet.py.
-- Derivative requirement: open_interest and iv are nullable so the SAME table
-- serves equities (always NULL) and options (populated) without a second schema.

CREATE TABLE prices (
    security_id     BIGINT NOT NULL REFERENCES security_master(security_id),
    price_date      DATE   NOT NULL,
    open            NUMERIC(18,6),
    high            NUMERIC(18,6),
    low             NUMERIC(18,6),
    close           NUMERIC(18,6),
    volume          BIGINT,
    open_interest   BIGINT,           -- derivatives only; NULL for cash instruments
    iv              NUMERIC(9,6),     -- implied vol; derivatives only
    source          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (security_id, price_date)
);
CREATE INDEX ix_prices_date ON prices(price_date);

CREATE TABLE macro_series (
    series_id   TEXT NOT NULL,               -- FRED code, e.g. 'DGS10'
    obs_date    DATE NOT NULL,
    value       NUMERIC(20,8),
    unit        TEXT,
    source      TEXT NOT NULL DEFAULT 'FRED',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (series_id, obs_date)
);

CREATE TABLE benchmarks (
    benchmark_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          TEXT NOT NULL,
    security_id   BIGINT REFERENCES security_master(security_id), -- representative index/ETF
    description   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE accounts ADD COLUMN benchmark_id BIGINT REFERENCES benchmarks(benchmark_id);
