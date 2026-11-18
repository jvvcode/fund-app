from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import settings


def _path(dataset: str) -> Path:
    p = Path(settings.parquet_root) / dataset
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_timeseries(dataset: str, df: pd.DataFrame) -> None:
    # Partition by date for fast range scans (the optimizer's dominant query pattern).
    df.to_parquet(_path(dataset), partition_cols=["date"], index=False)


def read_timeseries(dataset: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(_path(dataset), columns=columns)
