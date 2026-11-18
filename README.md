# fund-app — family fund management

Lean, Python-first framework for a sub-$10M family fund, built in five phases
(allocation & optimization is the priority; risk is embedded, not bolted on).
This repo's folder layout is fixed for the **whole project** from day one —
each module owns its folder from the start, even where the folder is a
Phase 2+/3+/5 stub today. That avoids restructuring the tree every time a new
phase starts.

## Quickstart (Phase 1)
1. `cp .env.example .env`
2. `make up`      — starts PostgreSQL 17 + TimescaleDB, genuinely empty (no auto-init)
3. `make setup`   — local venv + dev tooling + pre-commit
4. `make migrate` — `alembic upgrade head` creates the schema (same command in CI and on any machine)
5. `make seed`    — inserts a sample equity + an option written on it
6. `make test`

## Developing on Windows: use WSL2
Work inside WSL2 (Ubuntu), so the Makefile, Docker, CI and the eventual Linux
server all behave identically. Keep the repo in the Linux file system
(`~/projects/fund-app`), not under `/mnt/c/` — that's much slower. Turn on
Docker Desktop's WSL integration for Ubuntu, and open the repo with
`code .` (VS Code's WSL extension). Ubuntu also needs `python-is-python3`,
since the Makefile calls `python`. `.gitattributes` keeps line endings LF.

## Repo layout (all five phases)
```
fund-app/
├── .env / .env.example        secrets (gitignored) / template (committed)
├── docker-compose.yml         PostgreSQL 17 + TimescaleDB, + app container
├── pyproject.toml             dependencies (core + analytics + dev extras)
├── alembic.ini, migrations_alembic/   the ONLY schema mechanism, from commit 1
│   └── versions/               0001_initial_schema.py, 0002_market_data.py —
│                                each executes the matching db/migrations/*.sql
│                                verbatim, so the schema is plain, reviewable SQL
│                                *and* Alembic-tracked at the same time
├── db/
│   ├── migrations/            human-readable SQL source (not auto-applied —
│   │   ├── 0001_initial.sql       read by the Alembic revisions above)
│   │   │                          security_master, derivative_terms, accounts,
│   │   │                          transactions, tax_lots, positions
│   │   └── 0002_market_data.sql   prices, macro_series, benchmarks
│   └── seed/                  seed_universe.py — sample equity + option
├── src/fundapp/
│   ├── store/                 [Phase 1] SQLAlchemy models, engine, Parquet IO
│   ├── instruments/           [Phase 1] Instrument type hierarchy (cash + derivatives)
│   ├── ingestion/              [Phase 1] connectors, scheduler, derivative_watch
│   │   └── connectors/            polygon.py (wired — real grouped-daily fetch),
│   │                                fred.py, broker.py (fetch() still TODO)
│   ├── utils/                 [Phase 1] logging, config re-export
│   ├── portfolio/             [Phase 2 core; Phase 4 advanced] allocation & optimization
│   ├── analytics/             [Phase 2] CMA engine — expected returns, covariance
│   ├── risk/                  [Phase 3] VaR/CVaR, concentration, liquidity, limits
│   ├── api/                   [Phase 2+] FastAPI routes (services tier)
│   └── dashboard/             [Phase 2+] Streamlit UI
├── notebooks/                 research only — never imported by src/
├── tests/                     pytest — conftest.py, test_instruments.py,
│                               test_store.py, test_ingestion.py, test_polygon_connector.py
├── scripts/                   seed_securities.py, backfill_prices.py
├── data/                      Parquet time series (gitignored)
├── raw/                       untouched raw payloads per connector (gitignored)
└── .github/workflows/ci.yml   lint + test on push, against the real image (Postgres 17 + Timescale)
```

Order execution (Phase 2, manual) and finance & accounting (Phase 5, manual
initially) don't get dedicated `src/` packages yet — they're run by hand
against the ledger and positions tables until there's a workflow worth coding.
When they are: `src/fundapp/execution/` and `src/fundapp/accounting/`, same
pattern as the folders above.

## Derivative readiness (Phase 1 hooks)
- `security_master.instrument_type` discriminator; self-referential
  `underlying_security_id`; `contract_multiplier`; a `derivative_terms`
  extension table (strike, expiry, option type, exercise/settlement style,
  JSONB terms for the long tail).
- `positions.market_value` vs `positions.exposure` are separate columns —
  a future's market value is ~0, its exposure is not.
- `Instrument` class hierarchy (`instruments/base.py`) dispatches
  `market_value()` / `exposure()` by type; `cash.py` implements the linear
  case once, `derivatives.py` overrides exposure per instrument.
- `ingestion/connectors/broker.py` parses OCC option symbols and creates the
  `security_master` row (with `underlying_security_id`) on the fly if unseen.
- `ingestion/derivative_watch.py` flags positions expiring within N days,
  run nightly by the scheduler — so exercise/assignment/expiry is anticipated,
  not discovered after the fact in a broker statement.
- `prices.open_interest` / `prices.iv` are nullable columns on the *same*
  table equities use — no parallel schema for derivatives.

## Two conventions worth keeping
**`notebooks/` never imports from `src/`.** Notebooks are for exploration. If
you find yourself importing an `src/` module into a notebook, that code
belongs in `src/` with proper tests, not the other way around.

**`src/` never reads from `data/` or `raw/` by path.** Production code reads
via `fundapp.store` (`engine.py`, `parquet.py`). Hardcoded paths break inside
Docker and break again the day storage moves to S3.

**Every schema change is an Alembic revision — from the first table.**
PostgreSQL 17 + TimescaleDB starts empty; `make migrate` (`alembic upgrade head`) is the one
command that creates and updates the schema, identically on a laptop, in CI,
or on a machine nobody's set up yet. `db/migrations/*.sql` stay as the
plain-SQL source the first two revisions execute, so the schema is easy to
read *and* properly versioned — but there's no separate bootstrap-then-stamp
step to forget. The next schema change is `alembic revision -m "..."`, never
a manual `ALTER TABLE`.

**PostgreSQL 17 + TimescaleDB, locked from day one — no SQLite shortcut, ever.** `docker-compose.yml` and CI both run `timescale/timescaledb:latest-pg17` (Postgres 17 with the extension preloaded), and `0004_timescaledb.sql` enables it (`CREATE EXTENSION IF NOT EXISTS timescaledb`). Converting `prices` into a hypertable is deferred — the extension is on, but partitioning behavior is a deliberate, separate migration for when query volume actually calls for it, not something to do speculatively.

**Connectors are idempotent by construction, not by convention.** `prices` and
`macro_series` use `ON CONFLICT ... DO UPDATE` — safe, since those are refreshed
snapshots. `transactions` is immutable, so `broker.py` does more than dedupe:
on a repeated `external_ref` it distinguishes a true re-send (skip) from a
broker correction (different values — book a reversal + a corrected entry,
both linked via `related_txn_id` and `corrects_external_ref`) from a correction
already applied (skip). A *second* distinct correction to the same reference is
deliberately not auto-booked — it's logged as an error for manual entry, since
guessing which prior entry to reverse risks double-reversing the ledger.
