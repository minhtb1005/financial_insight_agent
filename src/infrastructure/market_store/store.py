"""SQLite snapshot store for market data (stdlib only, thread-safe, WAL).

Tables
------
- ``prices_daily``: daily OHLCV per (ticker, date).
- ``ratios_snapshot``: latest financial-ratio snapshot per (ticker, field).
- ``ingest_meta``: bookkeeping (backfill progress, last refresh, ...).

The DB file lives under ``data/`` (gitignored).  All timestamps are UTC ISO.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices_daily (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    source TEXT NOT NULL DEFAULT 'vnstock',
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, date)
);
CREATE TABLE IF NOT EXISTS ratios_snapshot (
    ticker TEXT NOT NULL,
    field TEXT NOT NULL,
    value REAL,
    period TEXT,
    source TEXT NOT NULL DEFAULT 'vnstock',
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, field)
);
CREATE TABLE IF NOT EXISTS ingest_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE INDEX IF NOT EXISTS idx_prices_ticker_date ON prices_daily(ticker, date);
CREATE TABLE IF NOT EXISTS prices_intraday (
    ticker TEXT NOT NULL,
    datetime TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    source TEXT NOT NULL DEFAULT 'vnstock',
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, datetime)
);
CREATE INDEX IF NOT EXISTS idx_intraday_ticker_dt ON prices_intraday(ticker, datetime);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class MarketStore:
    """Thread-safe SQLite store for daily prices + ratio snapshots."""

    def __init__(self, db_path: str | Path = "data/market_store.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False, timeout=30
        )
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ------------------------------------------------------------------
    # prices
    # ------------------------------------------------------------------

    def get_prices(
        self, ticker: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Rows in [start_date, end_date] ordered by date (each has fetched_at)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT date, open, high, low, close, volume, source, fetched_at"
                " FROM prices_daily WHERE ticker=? AND date>=? AND date<=?"
                " ORDER BY date ASC",
                (ticker.upper(), start_date, end_date),
            ).fetchall()
        return [dict(r) for r in rows]

    def upsert_prices(
        self, ticker: str, rows: list[dict[str, Any]], source: str = "vnstock"
    ) -> int:
        """Insert/replace daily rows. Returns number of rows written."""
        now = _utcnow()
        ticker = ticker.upper()
        payload = []
        for r in rows:
            date = str(r.get("date", ""))[:10]
            if not date:
                continue
            payload.append((
                ticker, date, r.get("open"), r.get("high"), r.get("low"),
                r.get("close"), r.get("volume"), source, now,
            ))
        if not payload:
            return 0
        with self._lock:
            self._conn.executemany(
                "INSERT OR REPLACE INTO prices_daily"
                " (ticker, date, open, high, low, close, volume, source, fetched_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                payload,
            )
            self._conn.commit()
        return len(payload)

    def coverage(self, ticker: str) -> dict[str, Any]:
        """Min/max date, row count and latest fetch time for a ticker."""
        with self._lock:
            row = self._conn.execute(
                "SELECT MIN(date) AS dmin, MAX(date) AS dmax, COUNT(*) AS n,"
                " MAX(fetched_at) AS latest FROM prices_daily WHERE ticker=?",
                (ticker.upper(),),
            ).fetchone()
        return {
            "ticker": ticker.upper(),
            "min_date": row["dmin"],
            "max_date": row["dmax"],
            "rows": row["n"],
            "latest_fetch": row["latest"],
        }

    def upsert_intraday(
        self, ticker: str, rows: list[dict[str, Any]], source: str = "vnstock"
    ) -> int:
        """Insert/replace intraday rows keyed (ticker, datetime)."""
        now = _utcnow()
        ticker = ticker.upper()
        payload = []
        for r in rows:
            dt = str(r.get("datetime") or r.get("date") or "")[:16]
            if not dt:
                continue
            payload.append((
                ticker, dt, r.get("open"), r.get("high"), r.get("low"),
                r.get("close"), r.get("volume"), source, now,
            ))
        if not payload:
            return 0
        with self._lock:
            self._conn.executemany(
                "INSERT OR REPLACE INTO prices_intraday"
                " (ticker, datetime, open, high, low, close, volume, source, fetched_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                payload,
            )
            self._conn.commit()
        return len(payload)

    def intraday_coverage(self, ticker: str) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT MIN(datetime) AS dmin, MAX(datetime) AS dmax, COUNT(*) AS n,"
                " MAX(fetched_at) AS latest FROM prices_intraday WHERE ticker=?",
                (ticker.upper(),),
            ).fetchone()
        return {"ticker": ticker.upper(), "min_dt": row["dmin"],
                "max_dt": row["dmax"], "rows": row["n"], "latest_fetch": row["latest"]}

    # ------------------------------------------------------------------
    # ratios
    # ------------------------------------------------------------------

    def save_ratios(
        self,
        ticker: str,
        ratios: dict[str, Any],
        period: str | None = None,
        source: str = "vnstock",
    ) -> int:
        """Upsert ratio snapshot fields. Returns number of fields written."""
        now = _utcnow()
        ticker = ticker.upper()
        payload = [
            (ticker, field, float(value), period, source, now)
            for field, value in (ratios or {}).items()
            if value is not None
        ]
        if not payload:
            return 0
        with self._lock:
            self._conn.executemany(
                "INSERT OR REPLACE INTO ratios_snapshot"
                " (ticker, field, value, period, source, fetched_at)"
                " VALUES (?,?,?,?,?,?)",
                payload,
            )
            self._conn.commit()
        return len(payload)

    def get_ratios(self, ticker: str) -> dict[str, Any]:
        """Latest snapshot per field + freshness of the snapshot."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT field, value, period, source, fetched_at FROM ratios_snapshot"
                " WHERE ticker=?",
                (ticker.upper(),),
            ).fetchall()
        out = {r["field"]: r["value"] for r in rows}
        if rows:
            out["_fetched_at"] = max(r["fetched_at"] for r in rows)
            out["_source"] = rows[0]["source"]
            periods = sorted({r["period"] for r in rows if r["period"]})
            if periods:
                out["_period"] = periods[-1]
        return out

    # ------------------------------------------------------------------
    # meta / bookkeeping
    # ------------------------------------------------------------------

    def get_meta(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM ingest_meta WHERE key=?", (key,)
            ).fetchone()
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

    # ponytail demo check: intraday roundtrip (run: python -m src.infrastructure.market_store.store)
    @staticmethod
    def demo() -> None:  # pragma: no cover
        s = MarketStore(db_path=":memory:")
        n = s.upsert_intraday("VCB", [{"datetime": "2026-10-15 10:00", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 3}])
        assert n == 1 and s.intraday_coverage("VCB")["rows"] == 1
        s.close()
