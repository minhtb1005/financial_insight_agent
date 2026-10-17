"""Financial adapter (vnstock 3.5.1, correct API).

``Company`` has no ``financial_statement``/``market_data`` on 3.5.1 —
the correct class is ``Finance`` (``ratio``/``balance_sheet``/...).
VCI is tried first with KBS fallback; total failure returns an empty
frame (never raises) so callers degrade to DB-partial/error dicts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from shared.ports.financial_port import FinancialPort

logger = logging.getLogger(__name__)


class FinancialAdapter(FinancialPort):
    def get_financial_statement(self, ticker: str) -> Any:
        from vnstock.api.financial import Finance

        ticker = (ticker or "").upper()
        last_error: Exception | None = None
        # KBS first: fresh periods (2026-Qx verified); VCI ratio is stale
        # (2018 only, verified 10/09/2026) so it is fallback-only.
        for source in ("KBS", "VCI"):
            try:
                return Finance(source=source, symbol=ticker, show_log=False).ratio()
            except Exception as e:
                last_error = e
                logger.warning("Finance.ratio %s %s failed: %s", source, ticker, e)
        logger.error("Finance.ratio all sources failed for %s: %s", ticker, last_error)
        return pd.DataFrame()

    def get_market_data(self, ticker: str) -> Any:
        """Latest close via Quote history (reliable path). Returns {} on failure."""
        from vnstock.api.quote import Quote

        ticker = (ticker or "").upper()
        try:
            end = datetime.now(timezone.utc).date()
            start = end - timedelta(days=7)
            df = Quote(source="VCI", symbol=ticker, show_log=False).history(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval="1D",
            )
            if df is None or getattr(df, "empty", False):
                return {}
            closes = df["close"].dropna() if "close" in df.columns else []
            if len(closes) == 0:
                return {}
            return {"current_price": float(closes.iloc[-1])}
        except Exception as e:
            logger.warning("Quote.history %s failed: %s", ticker, e)
            return {}
