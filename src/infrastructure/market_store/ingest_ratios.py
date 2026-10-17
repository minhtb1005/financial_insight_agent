"""Ratio snapshot ingest: quarterly backfill + refresh (Phase 4a debt).

Mirrors :mod:`infrastructure.market_store.ingest` discipline — one call
per ticker with sleep (Guest 20 req/min), resumable via ``ingest_meta``,
never raises on per-ticker failure. Snapshots store canonical computed
values (``pe``/``pb``/``roe``/...) so tools serve from DB without API.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from infrastructure.market_store.pilot import PILOT_TICKERS, RATIO_FIELDS
from infrastructure.market_store.store import MarketStore

if TYPE_CHECKING:
    from shared.ports.financial_port import FinancialPort

logger = logging.getLogger(__name__)

_DEFAULT_SLEEP_S = 5.0


def _compute_snapshot(port: FinancialPort, ticker: str) -> tuple[dict[str, float], str | None]:
    from application.services.financial.financial_ratio_service import (
        get_financial_ratios,
        parse_ratio_frame,
    )

    frame = port.get_financial_statement(ticker)
    vals, period = parse_ratio_frame(frame)
    if vals:
        return {k: v for k, v in vals.items() if k in RATIO_FIELDS}, period
    # Legacy fallback: balance-sheet compute path via the service helper.
    res = get_financial_ratios(port, ticker, None)
    if not isinstance(res, dict) or "error" in res:
        raise RuntimeError(
            str(res.get("error", "empty ratios")) if isinstance(res, dict) else "empty ratios"
        )
    out: dict[str, float] = {}
    period = None
    legacy_key = {
        "pe": "pe_ratio",
        "pb": "pb_ratio",
        "roe": "roe",
        "eps": "eps",
        "current_ratio": "current_ratio",
        "debt_to_equity": "debt_to_equity",
        "profit_margin": "profit_margin",
        "quick_ratio": "quick_ratio",
        "asset_turnover": "asset_turnover",
        "dividend_yield": "dividend_yield",
    }
    for field in RATIO_FIELDS:
        entry = res.get(legacy_key.get(field, field))
        if isinstance(entry, dict) and entry.get("value") is not None:
            out[field] = float(entry["value"])
            period = period or entry.get("time_range")
    if not out:
        raise RuntimeError("no ratios calculated")
    return out, period


def backfill_ratios(
    tickers: list[str] | None = None,
    port: FinancialPort | None = None,
    store: MarketStore | None = None,
    sleep_s: float = _DEFAULT_SLEEP_S,
) -> dict[str, Any]:
    """One snapshot per ticker into ``ratios_snapshot`` (resumable)."""
    from infrastructure.adapters.financial_adapter import FinancialAdapter

    tickers = [t.upper() for t in (tickers or PILOT_TICKERS)]
    port = port or FinancialAdapter()
    store = store or MarketStore()
    done, skipped, failed = [], [], {}
    for i, ticker in enumerate(tickers):
        if store.get_meta(f"ratios_{ticker}") == "done":
            skipped.append(ticker)
            continue
        try:
            vals, period = _compute_snapshot(port, ticker)
            n = store.save_ratios(ticker, vals, period=period, source="vnstock")
            if not n:
                raise RuntimeError("empty ratios")
            store.set_meta(f"ratios_{ticker}", "done")
            logger.info("Backfilled ratios %s: %d fields (%s)", ticker, n, period)
            done.append(ticker)
        except Exception as e:
            logger.warning("Backfill ratios %s failed: %s", ticker, e)
            failed[ticker] = str(e)[:200]
        if i < len(tickers) - 1:
            time.sleep(sleep_s)
    store.set_meta("ratios_last_run", datetime.now(timezone.utc).isoformat())
    return {"done": done, "skipped": skipped, "failed": failed}


def refresh_ratios(
    tickers: list[str] | None = None,
    port: FinancialPort | None = None,
    store: MarketStore | None = None,
    sleep_s: float = 2.0,
    force: bool = False,
) -> dict[str, Any]:
    """Quarterly refresh (manual or scheduler). ``force`` ignores resume marks."""
    from infrastructure.adapters.financial_adapter import FinancialAdapter

    tickers = [t.upper() for t in (tickers or PILOT_TICKERS)]
    port = port or FinancialAdapter()
    store = store or MarketStore()
    refreshed, failed = [], {}
    for i, ticker in enumerate(tickers):
        try:
            vals, period = _compute_snapshot(port, ticker)
            n = store.save_ratios(ticker, vals, period=period, source="vnstock")
            if force:
                store.set_meta(f"ratios_{ticker}", "done")
            refreshed.append((ticker, n))
        except Exception as e:
            logger.warning("Refresh ratios %s failed: %s", ticker, e)
            failed[ticker] = str(e)[:200]
        if i < len(tickers) - 1:
            time.sleep(sleep_s)
    store.set_meta("ratios_last_run", datetime.now(timezone.utc).isoformat())
    return {"refreshed": refreshed, "failed": failed}
