"""Rates SQL store (Layer-2 follow-up, pilot policy-SBV).

Mirrors ``infrastructure.market_store``: stdlib sqlite only, WAL,
threading.RLock, UTC ISO timestamps, DB file under ``data/`` (gitignored).
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS deposit_listed (
    bank TEXT NOT NULL,
    term_label TEXT NOT NULL,
    rate REAL NOT NULL,
    date TEXT NOT NULL,
    crawled_at TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (bank, term_label, date)
);
CREATE TABLE IF NOT EXISTS lending_listed (
    bank TEXT NOT NULL,
    loan_type TEXT NOT NULL,
    rate REAL NOT NULL,
    date TEXT NOT NULL,
    crawled_at TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (bank, loan_type, date)
);
CREATE TABLE IF NOT EXISTS avg_rates_monthly (
    category TEXT NOT NULL,
    month TEXT NOT NULL,
    value REAL NOT NULL,
    crawled_at TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (category, month)
);
CREATE TABLE IF NOT EXISTS policy_rates (
    rate_name TEXT NOT NULL,
    value REAL NOT NULL,
    effective_date TEXT NOT NULL,
    crawled_at TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (rate_name, effective_date)
);
CREATE TABLE IF NOT EXISTS vnibor_daily (
    term_label TEXT NOT NULL,
    rate REAL NOT NULL,
    date TEXT NOT NULL,
    crawled_at TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (term_label, date)
);
CREATE TABLE IF NOT EXISTS banks_meta (
    bank_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    extra TEXT,
    updated_at TEXT NOT NULL,
    source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingest_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE INDEX IF NOT EXISTS idx_deposit_bank_date ON deposit_listed(bank, date);
CREATE INDEX IF NOT EXISTS idx_lending_bank_date ON lending_listed(bank, date);
CREATE INDEX IF NOT EXISTS idx_vnibor_date ON vnibor_daily(date);
CREATE INDEX IF NOT EXISTS idx_policy_eff ON policy_rates(effective_date);
"""

# Retention per table in months; None = keep forever.
RETENTION_MONTHS: dict[str, int | None] = {
    "deposit_listed": 12,  # snapshot daily, giữ 6–12th
    "lending_listed": 12,  # weekly/khi đổi
    "avg_rates_monthly": None,  # SBV monthly, vĩnh viễn
    "policy_rates": None,  # SBV điều hành, vĩnh viễn
    "vnibor_daily": 6,  # daily, giữ 3–6th
    "banks_meta": None,  # lâu dài
}

# Column holding the snapshot date per table (for purge/stale).
_DATE_COL: dict[str, str] = {
    "deposit_listed": "date",
    "lending_listed": "date",
    "avg_rates_monthly": "month",
    "policy_rates": "effective_date",
    "vnibor_daily": "date",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RatesStore:
    """Thread-safe SQLite store for 6 rates groups."""

    def __init__(self, db_path: str | Path = "data/rates_store.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- deposit (daily listed) --
    def upsert_deposit(
        self,
        bank: str,
        term_label: str,
        rate: float,
        date: str,
        source: str = "sbv",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO deposit_listed"
                " (bank, term_label, rate, date, crawled_at, source)"
                " VALUES (?,?,?,?,?,?)",
                (bank, term_label, float(rate), date[:10], _utcnow(), source),
            )
            self._conn.commit()

    def get_deposit(
        self,
        bank: str | None = None,
        start: str = "",
        end: str = "",
    ) -> list[dict[str, Any]]:
        q = "SELECT bank, term_label, rate, date, crawled_at, source FROM deposit_listed WHERE 1=1"
        p: list[Any] = []
        if bank:
            q += " AND bank=?"
            p.append(bank)
        if start:
            q += " AND date>=?"
            p.append(start[:10])
        if end:
            q += " AND date<=?"
            p.append(end[:10])
        q += " ORDER BY date ASC"
        with self._lock:
            rows = self._conn.execute(q, p).fetchall()
        return [dict(r) for r in rows]

    # -- lending (weekly listed) --
    def upsert_lending(
        self,
        bank: str,
        loan_type: str,
        rate: float,
        date: str,
        source: str = "sbv",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO lending_listed"
                " (bank, loan_type, rate, date, crawled_at, source)"
                " VALUES (?,?,?,?,?,?)",
                (bank, loan_type, float(rate), date[:10], _utcnow(), source),
            )
            self._conn.commit()

    def get_lending(
        self,
        bank: str | None = None,
        start: str = "",
        end: str = "",
    ) -> list[dict[str, Any]]:
        q = "SELECT bank, loan_type, rate, date, crawled_at, source FROM lending_listed WHERE 1=1"
        p: list[Any] = []
        if bank:
            q += " AND bank=?"
            p.append(bank)
        if start:
            q += " AND date>=?"
            p.append(start[:10])
        if end:
            q += " AND date<=?"
            p.append(end[:10])
        q += " ORDER BY date ASC"
        with self._lock:
            rows = self._conn.execute(q, p).fetchall()
        return [dict(r) for r in rows]

    # -- avg monthly (SBV, keep forever) --
    def upsert_avg(
        self,
        category: str,
        month: str,
        value: float,
        source: str = "sbv",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO avg_rates_monthly"
                " (category, month, value, crawled_at, source)"
                " VALUES (?,?,?,?,?)",
                (category, month[:7], float(value), _utcnow(), source),
            )
            self._conn.commit()

    def get_avg(
        self,
        category: str | None = None,
        start: str = "",
        end: str = "",
    ) -> list[dict[str, Any]]:
        q = "SELECT category, month, value, crawled_at, source FROM avg_rates_monthly WHERE 1=1"
        p: list[Any] = []
        if category:
            q += " AND category=?"
            p.append(category)
        if start:
            q += " AND month>=?"
            p.append(start[:7])
        if end:
            q += " AND month<=?"
            p.append(end[:7])
        q += " ORDER BY month ASC"
        with self._lock:
            rows = self._conn.execute(q, p).fetchall()
        return [dict(r) for r in rows]

    # -- policy (SBV operating rates, keep forever) --
    def upsert_policy(
        self,
        rate_name: str,
        value: float,
        effective_date: str,
        source: str = "sbv",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO policy_rates"
                " (rate_name, value, effective_date, crawled_at, source)"
                " VALUES (?,?,?,?,?)",
                (rate_name, float(value), effective_date[:10], _utcnow(), source),
            )
            self._conn.commit()

    def get_policy(self, rate_name: str | None = None) -> list[dict[str, Any]]:
        q = "SELECT rate_name, value, effective_date, crawled_at, source FROM policy_rates WHERE 1=1"
        p: list[Any] = []
        if rate_name:
            q += " AND rate_name=?"
            p.append(rate_name)
        q += " ORDER BY effective_date ASC"
        with self._lock:
            rows = self._conn.execute(q, p).fetchall()
        return [dict(r) for r in rows]

    def latest_policy(self) -> dict[str, Any]:
        """Latest value per rate_name (each row carries effective_date/crawled_at/source)."""
        out: dict[str, Any] = {}
        for r in self.get_policy():
            out[r["rate_name"]] = r
        return out

    # -- vnibor daily --
    def upsert_vnibor(
        self,
        term_label: str,
        rate: float,
        date: str,
        source: str = "sbv",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO vnibor_daily"
                " (term_label, rate, date, crawled_at, source)"
                " VALUES (?,?,?,?,?)",
                (term_label, float(rate), date[:10], _utcnow(), source),
            )
            self._conn.commit()

    def get_vnibor(self, start: str = "", end: str = "") -> list[dict[str, Any]]:
        q = "SELECT term_label, rate, date, crawled_at, source FROM vnibor_daily WHERE 1=1"
        p: list[Any] = []
        if start:
            q += " AND date>=?"
            p.append(start[:10])
        if end:
            q += " AND date<=?"
            p.append(end[:10])
        q += " ORDER BY date ASC"
        with self._lock:
            rows = self._conn.execute(q, p).fetchall()
        return [dict(r) for r in rows]

    # -- banks meta (long-lived) --
    def upsert_bank(
        self,
        bank_code: str,
        name: str,
        extra: str = "",
        source: str = "sbv",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO banks_meta"
                " (bank_code, name, extra, updated_at, source)"
                " VALUES (?,?,?,?,?)",
                (bank_code, name, extra, _utcnow(), source),
            )
            self._conn.commit()

    def get_banks(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT bank_code, name, extra, updated_at, source"
                " FROM banks_meta ORDER BY bank_code ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    # -- retention / purge --
    def purge_older_than(self, table: str, cutoff: str) -> int:
        """Delete rows with snapshot date < cutoff (YYYY-MM-DD or YYYY-MM). Returns deleted count."""
        if table not in _DATE_COL:
            raise ValueError(f"no purgeable date column for {table!r}")
        col = _DATE_COL[table]
        with self._lock:
            cur = self._conn.execute(f"DELETE FROM {table} WHERE {col} < ?", (cutoff,))
            self._conn.commit()
            return cur.rowcount or 0

    def purge_expired(self, today: str | None = None) -> dict[str, int]:
        """Purge per-table retention (months) relative to today. Tables with None are skipped."""
        from datetime import timedelta

        ref = datetime.strptime((today or _utcnow()[:10]), "%Y-%m-%d")
        out: dict[str, int] = {}
        for table, months in RETENTION_MONTHS.items():
            if months is None:
                out[table] = 0
                continue
            cutoff = ref - timedelta(
                days=months * 30
            )  # ponytail: 30d/month approx, per-table months if finer needed
            fmt = "%Y-%m" if table == "avg_rates_monthly" else "%Y-%m-%d"
            out[table] = self.purge_older_than(table, cutoff.strftime(fmt))
        return out

    # -- freshness helpers (nhịp 2 dùng cho stale check) --
    def latest_fetch(self, table: str) -> str | None:
        col = "updated_at" if table == "banks_meta" else "crawled_at"
        with self._lock:
            row = self._conn.execute(f"SELECT MAX({col}) AS m FROM {table}").fetchone()
        return row["m"] if row and row["m"] else None

    def is_stale(self, table: str, max_age_hours: float) -> bool:
        """True khi chưa có dữ liệu hoặc fetch mới nhất quá hạn."""
        latest = self.latest_fetch(table)
        if not latest:
            return True
        try:
            dt = datetime.fromisoformat(latest)
        except ValueError:
            return True
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return age_h > max_age_hours

    # -- meta --
    def get_meta(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM ingest_meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO ingest_meta (key, value) VALUES (?,?)",
                (key, value),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
