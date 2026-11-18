from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://fund:fund@localhost:5432/fund"
    parquet_root: str = "./data/parquet"
    base_currency: str = "USD"

    polygon_api_key: str = ""
    fred_api_key: str = ""
    openfigi_api_key: str = ""

    # Polygon.io rebranded to Massive on Oct 30, 2025 (tracked as CL-2026-001).
    # Both domains serve identical data with the same API key; api.massive.com
    # is the forward-looking default per the vendor's own SDKs, with
    # api.polygon.io kept available below as an easy override if preferred.
    polygon_base_url: str = "https://api.massive.com"


settings = Settings()
