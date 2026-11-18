"""CMA engine: expected returns and covariance (EWMA, shrinkage) computed from
fundapp.store.parquet time series. Phase 2 for the baseline estimators; Phase 4
adds factor models. Results are written to an analytics cache, not recomputed
on every read.
"""
