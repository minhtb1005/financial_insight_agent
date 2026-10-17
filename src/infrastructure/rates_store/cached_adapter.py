"""SQL-first read adapter for rates_store (mirror CachedMarketDataAdapter).

Mỗi response kèm freshness công khai: ``data_as_of`` (crawled_at mới nhất),
``source`` (db | refreshed | db-partial) và ``stale`` (bool). Chỉ nhóm
policy có ingester thật (pilot SBV static); các nhóm daily (deposit/vnibor)
trả DB + cờ stale để caller quyết định crawl (ingester follow-up riêng).
"""

from __future__ import annotations

import contextlib
from typing import Any

from infrastructure.rates_store.store import RatesStore

# Ngưỡng stale theo spec: huy động 12–24h; SBV policy/avg >1 tháng.
STALE_HOURS: dict[str, float] = {
    "deposit_listed": 24,
    "lending_listed": 168,
    "avg_rates_monthly": 720,
    "policy_rates": 720,
    "vnibor_daily": 24,
    "banks_meta": 720,
}


class RatesCachedAdapter:
    def __init__(self, store: RatesStore | None = None) -> None:
        self._store = store or RatesStore()

    @property
    def store(self) -> RatesStore:
        return self._store

    def get(
        self,
        group: str,
        bank: str | None = None,
        start: str = "",
        end: str = "",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Đọc SQL-first; policy tự refresh khi stale/force, nhóm khác trả DB + stale flag."""
        if group == "policy":
            if force_refresh or self._store.is_stale("policy_rates", STALE_HOURS["policy_rates"]):
                from infrastructure.rates_store.ingest import ingest_policy_rates

                with contextlib.suppress(Exception):  # rớt về DB cũ (db-partial)
                    ingest_policy_rates(self._store)
            rows = self._store.get_policy()
            return self._shape(group, rows, "refreshed" if force_refresh else "db")
        if group == "deposit":
            rows = self._store.get_deposit(bank, start, end)
            table = "deposit_listed"
        elif group == "lending":
            rows = self._store.get_lending(bank, start, end)
            table = "lending_listed"
        elif group == "avg":
            rows = self._store.get_avg(bank, start, end)
            table = "avg_rates_monthly"
        elif group == "vnibor":
            rows = self._store.get_vnibor(start, end)
            table = "vnibor_daily"
        elif group == "banks":
            rows = self._store.get_banks()
            table = "banks_meta"
        else:
            return {
                "error": f"unknown group: {group}",
                "valid_groups": ["policy", "deposit", "lending", "avg", "vnibor", "banks"],
            }
        stale = self._store.is_stale(table, STALE_HOURS[table])
        return self._shape(group, rows, "db", stale=stale)

    @staticmethod
    def _shape(
        group: str, rows: list[dict[str, Any]], source: str, stale: bool = False
    ) -> dict[str, Any]:
        stamps = [
            r.get("crawled_at") or r.get("updated_at")
            for r in rows
            if r.get("crawled_at") or r.get("updated_at")
        ]
        return {
            "group": group,
            "data": rows,
            "data_as_of": max(stamps) if stamps else None,
            "source": "db-partial" if (rows and stale) else source,
            "stale": stale,
        }
