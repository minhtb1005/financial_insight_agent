"""Ingest jobs: one-off backfill + periodic today-refresh (Phase 4a pilot).

Rate-limit discipline (vnstock Guest: 20 req/min): one range call per ticker
with a sleep between tickers, progress tracked in ``ingest_meta`` so an
interrupted run resumes where it stopped.  Never raises on a per-ticker
failure — records the error and continues.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from shared.ports.market_data_port import MarketDataPort
from infrastructure.market_store.pilot import (
    BACKFILL_START,
    PILOT_TICKERS,
    REFRESH_LOOKBACK_DAYS,
)
from infrastructure.market_store.store import MarketStore

logger = logging.getLogger(__name__)

_DEFAULT_SLEEP_S = 5.0


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def backfill(
    tickers: list[str] | None = None,
    start: str = BACKFILL_START,
    port: MarketDataPort | None = None,
    store: MarketStore | None = None,
    sleep_s: float = _DEFAULT_SLEEP_S,
) -> dict[str, Any]:
    """Fetch full daily history per ticker (one range call each) into the store."""
    from infrastructure.adapters.vn_stock_adapter import VNStockAdapter

    tickers = [t.upper() for t in (tickers or PILOT_TICKERS)]
    port = port or VNStockAdapter()
    store = store or MarketStore()
    end = _today()
    done, skipped, failed = [], [], {}
    for i, ticker in enumerate(tickers):
        if store.get_meta(f"backfill_{ticker}") == "done":
            skipped.append(ticker)
            continue
        try:
            payload = port.get_price_data(ticker, start, end)
            if not isinstance(payload, dict) or "error" in payload or not payload.get("data"):
                raise RuntimeError(str(payload.get("error", "empty data") if isinstance(payload, dict) else payload))
            n = store.upsert_prices(ticker, payload["data"], source="vnstock")
            store.set_meta(f"backfill_{ticker}", "done")
            logger.info("Backfilled %s: %d rows (%s..%s)", ticker, n, start, end)
            done.append(ticker)
        except Exception as e:
            # Rate-limit deaths can kill the process; progress so far is kept.
            logger.warning("Backfill %s failed: %s", ticker, e)
            failed[ticker] = str(e)[:200]
        if i < len(tickers) - 1:
            time.sleep(sleep_s)
    store.set_meta("backfill_last_run", datetime.now(timezone.utc).isoformat())
    return {"done": done, "skipped": skipped, "failed": failed}


def refresh_today(
    tickers: list[str] | None = None,
    lookback_days: int = REFRESH_LOOKBACK_DAYS,
    port: MarketDataPort | None = None,
    store: MarketStore | None = None,
    sleep_s: float = 2.0,
) -> dict[str, Any]:
    """Refresh recent bars (overlap catches late corrections). Runs every 10-20 min."""
    from infrastructure.adapters.vn_stock_adapter import VNStockAdapter

    tickers = [t.upper() for t in (tickers or PILOT_TICKERS)]
    port = port or VNStockAdapter()
    store = store or MarketStore()
    end = datetime.now(timezone.utc)
    start = (end - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")
    refreshed, failed = [], {}
    for i, ticker in enumerate(tickers):
        try:
            payload = port.get_price_data(ticker, start, end_s)
            if not isinstance(payload, dict) or "error" in payload or not payload.get("data"):
                raise RuntimeError(str(payload.get("error", "empty data") if isinstance(payload, dict) else payload))
            n = store.upsert_prices(ticker, payload["data"], source="vnstock")
            refreshed.append((ticker, n))
        except Exception as e:
            logger.warning("Refresh %s failed: %s", ticker, e)
            failed[ticker] = str(e)[:200]
        if i < len(tickers) - 1:
            time.sleep(sleep_s)
    store.set_meta("refresh_last_run", datetime.now(timezone.utc).isoformat())
    return {"refreshed": refreshed, "failed": failed}
