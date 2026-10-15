"""Phase 4b nhịp-a: VN30 → HOSE daily 2-3y (gate) + intraday VN30 pilot.

VN30 list: snapshot rổ công bố 2025 (ghi rõ ngày). Gate: VN30 xanh mới mở
HNX/UPCoM. Intraday pilot: 5 mã đầu VN30, interval 1h, 3 tháng gần nhất.
Postgres + cron ngoài là nhịp-c (chưa trong file này).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Snapshot rổ VN30 công bố 2025 (30 mã, source: HSX công bố rổ kỳ 2025).
VN30_2025: list[str] = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "LPB", "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI",
    "STB", "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB",
]

INTRADAY_PILOT: list[str] = ["VCB", "HPG", "FPT", "VNM", "BID"]


def backfill_universe(
    tickers: list[str],
    start: str,
    store=None,
    sleep_s: float = 3.0,
) -> dict[str, Any]:
    """Daily backfill cho universe (tái dùng ingest.backfill, meta key riêng)."""
    from infrastructure.market_store.ingest import backfill

    res = backfill(tickers=tickers, start=start, store=store, sleep_s=sleep_s)
    done = res.get("done", [])
    failed = res.get("failed", {})
    cov: dict[str, Any] = {}
    if store is not None:
        for t in done:
            cov[t] = store.coverage(t)
    total = len(tickers)
    ok_rate = len(done) / total if total else 0.0
    return {"done": done, "failed": failed, "coverage": cov,
            "ok_rate": round(ok_rate, 3), "start": start}


def backfill_intraday_pilot(
    tickers: list[str] | None = None,
    months: int = 3,
    store=None,
    sleep_s: float = 3.0,
) -> dict[str, Any]:
    """Intraday pilot: interval 1h, N tháng gần nhất, vào prices_intraday."""
    from infrastructure.adapters.vn_stock_adapter import VNStockAdapter
    from infrastructure.market_store.store import MarketStore

    tickers = [t.upper() for t in (tickers or INTRADAY_PILOT)]
    store = store or MarketStore()
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=months * 30)).strftime("%Y-%m-%d")
    port = VNStockAdapter()
    done, failed, rows = [], {}, {}
    for i, ticker in enumerate(tickers):
        try:
            payload = port.get_price_data(ticker, start, end, interval="1h")
            if not isinstance(payload, dict) or "error" in payload or not payload.get("data"):
                raise RuntimeError(str(payload.get("error", "empty") if isinstance(payload, dict) else payload))
            data = payload["data"]
            norm = [{"datetime": str(r.get("date", ""))[:16], **{k: r.get(k) for k in ("open", "high", "low", "close", "volume")}} for r in data]
            n = store.upsert_intraday(ticker, norm)
            rows[ticker] = n
            done.append(ticker)
        except Exception as e:
            logger.warning("Intraday %s failed: %s", ticker, e)
            failed[ticker] = str(e)[:200]
        if i < len(tickers) - 1:
            time.sleep(sleep_s)
    return {"done": done, "failed": failed, "rows": rows, "start": start, "end": end}
