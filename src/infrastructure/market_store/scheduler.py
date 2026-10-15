"""In-app scheduler for the market-data refresh job (Phase 4a pilot).

Mirrors ``infrastructure.rag.scheduler`` conventions: APScheduler
BackgroundScheduler, Asia/Ho_Chi_Minh timezone, opt-in via env flag,
idempotent start/stop.  Refresh cadence comes from ``pilot.REFRESH_MINUTES``.
"""

from __future__ import annotations

import os
from zoneinfo import ZoneInfo

from infrastructure.observability import get_logger

logger = get_logger("market_store.scheduler")

_scheduler = None


def start_market_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    if os.getenv("ENABLE_MARKET_SCHEDULER", "false").lower() not in ("1", "true", "yes"):
        logger.info("Market scheduler disabled (ENABLE_MARKET_SCHEDULER!=true)")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        from infrastructure.market_store.ingest import refresh_today
        from infrastructure.market_store.pilot import PILOT_TICKERS, REFRESH_MINUTES

        def job() -> None:
            logger.info("Market refresh job start (%d tickers)", len(PILOT_TICKERS))
            try:
                res = refresh_today(PILOT_TICKERS)
                logger.info("Market refresh job done: %s", res)
            except Exception as e:
                logger.exception("Market refresh job failed: %s", e)

        def ratios_job() -> None:
            logger.info("Ratios refresh job start (%d tickers)", len(PILOT_TICKERS))
            try:
                from infrastructure.market_store.ingest_ratios import refresh_ratios

                res = refresh_ratios(PILOT_TICKERS)
                logger.info("Ratios refresh job done: %s", res)
            except Exception as e:
                logger.exception("Ratios refresh job failed: %s", e)

        sched = BackgroundScheduler(timezone=ZoneInfo("Asia/Ho_Chi_Minh"))
        sched.add_job(
            job,
            IntervalTrigger(minutes=REFRESH_MINUTES),
            id="market_refresh",
            replace_existing=True,
        )
        sched.add_job(
            ratios_job,
            IntervalTrigger(days=90),
            id="ratios_refresh",
            replace_existing=True,
        )
        sched.start()
        _scheduler = sched
        logger.info(
            "Market scheduler started — every %d min Asia/Ho_Chi_Minh", REFRESH_MINUTES
        )
    except Exception as e:
        logger.warning("Failed to start market scheduler: %s", e)


def stop_market_scheduler() -> None:
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
