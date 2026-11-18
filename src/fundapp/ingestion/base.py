from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from config.settings import settings


class Connector(ABC):
    # One connector per external source, behind a common interface so providers
    # are swappable. Idempotent by contract: fetching the same window twice yields
    # the same result and never duplicates.
    name: str = "connector"

    @abstractmethod
    def fetch(self, as_of: date):
        # Return the native payload for a given date (or range).
        ...

    def land_raw(self, as_of: date, payload) -> Path:
        # Persist the untouched payload before any parsing — enables audit and
        # reprocessing when a normalization bug is found later.
        root = Path(settings.parquet_root).parent / "raw" / self.name
        root.mkdir(parents=True, exist_ok=True)
        fp = root / f"{as_of.isoformat()}.json"
        fp.write_text(json.dumps(payload, default=str))
        return fp
