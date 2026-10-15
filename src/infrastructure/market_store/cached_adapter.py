"""Read-through MarketDataPort: sqlite snapshot first, vnstock on miss/stale.

Response shape is a superset of :class:`VNStockAdapter` with two extra keys
so freshness is public to every consumer (tools → agent → user):

- ``data_as_of``: max ``fetched_at`` (UTC ISO) of the returned rows.
- ``source``: ``"db"`` (fully cached) | ``"vnstock"`` (fully fresh) | ``"mixed"``.

Only ``interval="1d"`` is cached (pilot scope); other intervals delegate
straight to the inner port.  Behaviour is never worse than the inner port:
on upstream error with an empty store the inner error is returned; with a
partial store the partial rows are returned with ``source="db-partial"``.
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any

from shared.ports.market_data_port import MarketDataPort
from infrastructure.market_store.store import MarketStore


def _norm_date(value: Any) -> str:
    return str(value or "")[:10]


class CachedMarketDataAdapter(MarketDataPort):
    def __init__(
        self, inner: MarketDataPort, store: MarketStore | None = None
    ) -> None:
        self._inner = inner
        self._store = store or MarketStore()

    @property
    def store(self) -> MarketStore:
        return self._store

    def get_price_data(
        self, ticker: str, start_date: str, end_date: str, interval: str = "1d"
    ) -> dict[str, Any]:
        ticker = (ticker or "").upper()
        if not ticker:
            return {"error": "Missing ticker"}
        if interval != "1d":
            fresh = self._inner.get_price_data(ticker, start_date, end_date, interval)
            if isinstance(fresh, dict) and "error" not in fresh:
                fresh["data_as_of"] = datetime.now(timezone.utc).isoformat()
                fresh["source"] = "vnstock"
            return fresh

        cached = self._store.get_prices(ticker, start_date, end_date)
        have = {r["date"] for r in cached}
        missing = self._missing_dates(start_date, end_date, have)
        if not missing:
            return self._shape(ticker, cached, start_date, end_date, "db")

        fresh = self._inner.get_price_data(ticker, missing[0], missing[-1], interval)
        if not isinstance(fresh, dict) or "error" in fresh or not fresh.get("data"):
            if cached:
                return self._shape(ticker, cached, start_date, end_date, "db-partial")
            return fresh if isinstance(fresh, dict) else {"error": "No data available"}

        self._store.upsert_prices(ticker, fresh.get("data", []), source="vnstock")
        merged = self._store.get_prices(ticker, start_date, end_date) or cached
        grew = bool(cached) and len(merged) > len(cached)
        return self._shape(
            ticker, merged, start_date, end_date, "mixed" if grew else "vnstock"
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _missing_dates(
        start_date: str, end_date: str, have: set[str]
    ) -> list[str]:
        """Missing dates in [start_date, end_date]; caller fetches one span."""
        try:
            start = date.fromisoformat(start_date[:10])
            end = date.fromisoformat(end_date[:10])
        except ValueError:
            return [start_date, end_date]
        if end < start:
            return []
        missing = []
        day = start
        while day <= end:
            if day.isoformat() not in have:
                missing.append(day.isoformat())
            day = day + timedelta(days=1)
        return missing

    @staticmethod
    def _shape(
        ticker: str,
        rows: list[dict[str, Any]],
        start_date: str,
        end_date: str,
        source: str,
    ) -> dict[str, Any]:
        data = [
            {
                "date": _norm_date(r.get("date")),
                "open": r.get("open"),
                "high": r.get("high"),
                "low": r.get("low"),
                "close": r.get("close"),
                "volume": r.get("volume"),
            }
            for r in rows
        ]
        stamps = [r.get("fetched_at") for r in rows if r.get("fetched_at")]
        return {
            "ticker": ticker,
            "data": data,
            "start_date": start_date,
            "end_date": end_date,
            "data_as_of": max(stamps) if stamps else None,
            "source": source,
        }
