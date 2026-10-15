"""In-app scheduler for rates refresh (opt-in, mirror market_store.scheduler).

Policy SBV đổi hiếm → check mỗi 7 ngày. Deposit/VNIBOR daily là follow-up
(ingester riêng) nên scheduler hiện chỉ refresh policy.
"""

from __future__ import annotations

import os
from zoneinfo import ZoneInfo

from infrastructure.observability import get_logger

logger = get_logger("rates_store.scheduler")

_scheduler = None


def start_rates_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    if os.getenv("ENABLE_RATES_SCHEDULER", "false").lower() not in ("1", "true", "yes"):
        logger.info("Rates scheduler disabled (ENABLE_RATES_SCHEDULER!=true)")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        from infrastructure.rates_store.ingest import ingest_policy_rates
        from infrastructure.rates_store.store import RatesStore

        def job() -> None:
            try:
                res = ingest_policy_rates(RatesStore())
                logger.info("Rates policy refresh done: skipped=%s", res.get("skipped"))
            except Exception as e:
                logger.exception("Rates policy refresh failed: %s", e)

        sched = BackgroundScheduler(timezone=ZoneInfo("Asia/Ho_Chi_Minh"))
        sched.add_job(job, IntervalTrigger(days=7), id="rates_policy", replace_existing=True)
        sched.start()
        _scheduler = sched
        logger.info("Rates scheduler started — weekly Asia/Ho_Chi_Minh")
    except Exception as e:
        logger.warning("Failed to start rates scheduler: %s", e)


def stop_rates_scheduler() -> None:
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
