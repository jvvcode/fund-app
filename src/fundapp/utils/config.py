# Thin re-export so code under src/fundapp can `from fundapp.utils.config import settings`
# without reaching up to the repo-root config/ package directly. config/settings.py
# (pydantic BaseSettings, reads .env) remains the single source of truth.
from config.settings import settings  # noqa: F401
