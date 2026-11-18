from __future__ import annotations

from datetime import date

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from fundapp.ingestion.calendar import is_trading_day
from fundapp.ingestion.connectors.broker import BrokerImportConnector
from fundapp.ingestion.connectors.fred import FredMacroConnector
from fundapp.ingestion.connectors.polygon import PolygonPriceConnector
from fundapp.ingestion.derivative_watch import expiring_soon
from fundapp.store.engine import SessionLocal
from fundapp.utils.logging import get_logger

log = get_logger(__name__)


def run_price_ingestion() -> None:
    today = date.today()
    if not is_trading_day(today):
        log.info("%s is not a trading day — skipping price ingestion", today)
        return
    PolygonPriceConnector().run(today)


def run_broker_import() -> None:
    BrokerImportConnector().run(date.today())


def run_derivative_expiry_check() -> None:
    # Anticipate expiry/exercise/assignment before it shows up unexplained in a
    # broker statement.
    with SessionLocal() as s:
        soon = expiring_soon(s, days=5)
        if soon:
            log.warning("%d derivative position(s) expire within 5 days: %s", len(soon), soon)


def run_macro_update() -> None:
    FredMacroConnector().run(date.today())


def build_scheduler() -> BlockingScheduler:
    sched = BlockingScheduler(timezone="America/New_York")
    # Nightly, after market close (21:00 ET close-of-books check onward).
    sched.add_job(run_price_ingestion, CronTrigger(hour=22, minute=0), id="prices")
    sched.add_job(run_broker_import, CronTrigger(hour=22, minute=45), id="broker")
    sched.add_job(run_derivative_expiry_check, CronTrigger(hour=23, minute=0), id="expiry_check")
    sched.add_job(run_macro_update, CronTrigger(day_of_week="sun", hour=8, minute=0), id="macro")
    return sched


if __name__ == "__main__":
    build_scheduler().start()
