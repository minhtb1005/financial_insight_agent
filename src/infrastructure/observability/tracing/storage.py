"""Persistence layer for traces: SQLite primary store + optional JSONL mirror."""

from __future__ import annotations

import contextlib
import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    request_id TEXT,
    root_name TEXT,
    status TEXT DEFAULT 'running',
    started_at REAL,
    ended_at REAL,
    duration_ms REAL,
    num_spans INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    llm_call_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS spans (
    span_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    parent_span_id TEXT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    request_id TEXT,
    started_at REAL,
    ended_at REAL,
    duration_ms REAL,
    status TEXT,
    model TEXT,
    provider TEXT,
    prompt_name TEXT,
    prompt_version TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    inputs TEXT,
    outputs TEXT,
    attributes TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_traces_started ON traces(started_at DESC);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    span_id TEXT,
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    comment TEXT DEFAULT '',
    author TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_trace ON feedback(trace_id);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    span_id TEXT,
    author TEXT NOT NULL,
    comment TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comments_trace ON comments(trace_id);
"""

# Batch 2 nullable columns (SQLite ALTER ADD COLUMN, backward-compat, no alembic).
_EXTRA_TRACE_COLS: list[tuple[str, str]] = [
    ("session_id", "TEXT"),
    ("user_id", "TEXT"),
    ("version", "TEXT"),
    ("env", "TEXT"),
    ("cost", "REAL"),
    ("scores", "TEXT"),
    ("tags", "TEXT"),
]


class TraceStore:
    """Thread-safe SQLite storage for spans and trace summaries."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._ensure_extra_cols()
            self._conn.commit()

    def _ensure_extra_cols(self) -> None:
        """Thêm cột nullable Batch 2 nếu DB cũ chưa có (idempotent)."""
        existing = {r[1] for r in self._conn.execute("PRAGMA table_info(traces)").fetchall()}
        for col, typ in _EXTRA_TRACE_COLS:
            if col not in existing:
                self._conn.execute(f"ALTER TABLE traces ADD COLUMN {col} {typ}")

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def record_span(
        self,
        span_dict: dict[str, Any],
        inputs_json: str | None,
        outputs_json: str | None,
        attributes_json: str | None,
        is_root: bool,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO spans (
                    span_id, trace_id, parent_span_id, name, kind, request_id,
                    started_at, ended_at, duration_ms, status, model, provider,
                    prompt_name, prompt_version, prompt_tokens, completion_tokens,
                    total_tokens, inputs, outputs, attributes, error
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    span_dict["span_id"],
                    span_dict["trace_id"],
                    span_dict["parent_span_id"],
                    span_dict["name"],
                    span_dict["kind"],
                    span_dict["request_id"],
                    span_dict["started_at"],
                    span_dict["ended_at"],
                    span_dict["duration_ms"],
                    span_dict["status"],
                    span_dict["model"],
                    span_dict["provider"],
                    span_dict["prompt_name"],
                    span_dict["prompt_version"],
                    span_dict["prompt_tokens"],
                    span_dict["completion_tokens"],
                    span_dict["total_tokens"],
                    inputs_json,
                    outputs_json,
                    attributes_json,
                    span_dict["error"],
                ),
            )
            self._upsert_trace(span_dict, is_root)
            if is_root:
                self._conn.execute(
                    """UPDATE traces SET
                        status=CASE WHEN status='error' OR ?='error' THEN 'error' ELSE ? END,
                        ended_at=? WHERE trace_id=?""",
                    (
                        span_dict["status"],
                        span_dict["status"],
                        span_dict["ended_at"],
                        span_dict["trace_id"],
                    ),
                )
            self._refresh_trace_aggregates(span_dict["trace_id"])
            self._conn.commit()

    def _upsert_trace(self, span_dict: dict[str, Any], is_root: bool) -> None:
        root_name = span_dict["name"] if is_root else None
        self._conn.execute(
            """
            INSERT INTO traces (trace_id, request_id, root_name, status, started_at)
            VALUES (?,?,?, 'running', ?)
            ON CONFLICT(trace_id) DO UPDATE SET
                root_name = COALESCE(root_name, excluded.root_name),
                request_id = COALESCE(request_id, excluded.request_id)
            """,
            (
                span_dict["trace_id"],
                span_dict["request_id"],
                root_name,
                span_dict["started_at"],
            ),
        )

    def _refresh_trace_aggregates(self, trace_id: str) -> None:
        self._conn.execute(
            """
            UPDATE traces SET
                num_spans = (SELECT COUNT(*) FROM spans WHERE trace_id=:tid),
                total_tokens = (SELECT COALESCE(SUM(total_tokens), 0) FROM spans WHERE trace_id=:tid),
                llm_call_count = (SELECT COUNT(*) FROM spans WHERE trace_id=:tid AND kind='llm'),
                tool_call_count = (SELECT COUNT(*) FROM spans WHERE trace_id=:tid AND kind='tool'),
                started_at = COALESCE(
                    (SELECT MIN(started_at) FROM spans WHERE trace_id=:tid), started_at
                ),
                ended_at = COALESCE(
                    (SELECT MAX(ended_at) FROM spans WHERE trace_id=:tid), ended_at
                ),
                duration_ms = CASE WHEN (
                    SELECT MAX(ended_at) FROM spans WHERE trace_id=:tid
                ) IS NOT NULL THEN ROUND((
                    (SELECT MAX(ended_at) FROM spans WHERE trace_id=:tid) -
                    (SELECT MIN(started_at) FROM spans WHERE trace_id=:tid)
                ) * 1000, 2) ELSE duration_ms END,
                status = CASE WHEN EXISTS (
                    SELECT 1 FROM spans WHERE trace_id=:tid AND status='error'
                ) THEN 'error' ELSE status END
            WHERE trace_id=:tid
            """,
            {"tid": trace_id},
        )

    def purge_older_than(self, days: int) -> int:
        cutoff = time.time() - days * 86400
        with self._lock:
            cur = self._conn.execute("SELECT trace_id FROM traces WHERE started_at < ?", (cutoff,))
            ids = [r[0] for r in cur.fetchall()]
            for tid in ids:
                self._conn.execute("DELETE FROM spans WHERE trace_id=?", (tid,))
                self._conn.execute("DELETE FROM traces WHERE trace_id=?", (tid,))
            self._conn.commit()
        return len(ids)

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.commit()
                self._conn.close()
            except sqlite3.Error:
                pass

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_span(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        for key in ("inputs", "outputs", "attributes"):
            raw = d.get(key)
            if isinstance(raw, str):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d[key] = json.loads(raw)
        return d

    _SORTABLE = ("started_at", "duration_ms", "num_spans", "total_tokens")

    @staticmethod
    def _escape_like(s: str) -> str:
        return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _where_clause(  # noqa: PLR0917 - keep public signature
        self,
        status: str | None,
        min_duration_ms: float | None,
        name_filter: str | None,
        trace_id_search: str | None,
        from_ts: float | None,
        to_ts: float | None,
    ) -> tuple[str, list[Any]]:
        where = " WHERE 1=1"
        params: list[Any] = []
        if status:
            where += " AND status = ?"
            params.append(status)
        if min_duration_ms is not None:
            where += " AND duration_ms >= ?"
            params.append(min_duration_ms)
        if name_filter:
            where += " AND root_name LIKE ? ESCAPE '\\'"
            params.append(f"%{self._escape_like(name_filter)}%")
        if trace_id_search:
            where += " AND trace_id LIKE ? ESCAPE '\\'"
            params.append(f"%{self._escape_like(trace_id_search)}%")
        if from_ts is not None:
            where += " AND started_at >= ?"
            params.append(from_ts)
        if to_ts is not None:
            where += " AND started_at <= ?"
            params.append(to_ts)
        return where, params

    @staticmethod
    def _order_clause(sort_by: str, sort_dir: str) -> str:
        direction = "ASC" if sort_dir == "asc" else "DESC"
        if sort_by == "duration_ms":
            # NULL-cuoi cho trace running (duration_ms NULL)
            return f" ORDER BY duration_ms IS NULL ASC, duration_ms {direction}"
        return f" ORDER BY {sort_by} {direction}"

    def count_traces(  # noqa: PLR0917 - keep public signature
        self,
        status: str | None = None,
        min_duration_ms: float | None = None,
        name_filter: str | None = None,
        trace_id_search: str | None = None,
        from_ts: float | None = None,
        to_ts: float | None = None,
    ) -> int:
        where, params = self._where_clause(
            status, min_duration_ms, name_filter, trace_id_search, from_ts, to_ts
        )
        with self._lock:
            row = self._conn.execute(f"SELECT COUNT(*) AS n FROM traces{where}", params).fetchone()
        return int(row["n"]) if row else 0

    def list_traces(  # noqa: PLR0917 - keep public signature
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        min_duration_ms: float | None = None,
        name_filter: str | None = None,
        trace_id_search: str | None = None,
        from_ts: float | None = None,
        to_ts: float | None = None,
        sort_by: str = "started_at",
        sort_dir: str = "desc",
    ) -> list[dict[str, Any]]:
        if sort_by not in self._SORTABLE:
            sort_by = "started_at"
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"
        where, params = self._where_clause(
            status, min_duration_ms, name_filter, trace_id_search, from_ts, to_ts
        )
        query = (
            f"SELECT * FROM traces{where}{self._order_clause(sort_by, sort_dir)} LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._lock:
            trow = self._conn.execute(
                "SELECT * FROM traces WHERE trace_id=?", (trace_id,)
            ).fetchone()
            if trow is None:
                return None
            srows = self._conn.execute(
                "SELECT * FROM spans WHERE trace_id=? ORDER BY started_at ASC",
                (trace_id,),
            ).fetchall()
        trace = dict(trow)
        trace["spans"] = [self._row_to_span(r) for r in srows]
        return trace

    # ------------------------------------------------------------------
    # human feedback (admin-only via API)
    # ------------------------------------------------------------------

    def add_feedback(
        self,
        trace_id: str,
        score: int,
        comment: str = "",
        author: str = "",
        span_id: str | None = None,
    ) -> dict[str, Any]:
        """Chấm tay 1-5 sao cho trace (span_id NULL = cả trace). CHECK ở schema chặn score ngoài range."""
        from datetime import datetime, timezone as _tz

        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO feedback (trace_id, span_id, score, comment, author, created_at)"
                " VALUES (?,?,?,?,?,?)",
                (
                    trace_id,
                    span_id,
                    int(score),
                    comment or "",
                    author,
                    datetime.now(_tz.utc).isoformat(),
                ),
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM feedback WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        return dict(row)

    def list_feedback(self, trace_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM feedback WHERE trace_id=? ORDER BY id ASC",
                (trace_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # -- Batch 2: comments per node + meta nullable + DELETE --
    def add_comment(
        self,
        trace_id: str,
        comment: str,
        author: str = "",
        span_id: str | None = None,
    ) -> dict[str, Any]:
        from datetime import datetime, timezone as _tz

        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO comments (trace_id, span_id, author, comment, created_at)"
                " VALUES (?,?,?,?,?)",
                (trace_id, span_id, author, comment, datetime.now(_tz.utc).isoformat()),
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM comments WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        return dict(row)

    def list_comments(self, trace_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM comments WHERE trace_id=? ORDER BY id ASC",
                (trace_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def update_trace_meta(self, trace_id: str, fields: dict[str, Any]) -> None:
        allowed = {c for c, _ in _EXTRA_TRACE_COLS}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        with self._lock:
            self._conn.execute(
                f"UPDATE traces SET {', '.join(f'{k}=?' for k in sets)} WHERE trace_id=?",
                (*sets.values(), trace_id),
            )
            self._conn.commit()

    def delete_trace(self, trace_id: str) -> bool:
        """Xóa trace + spans + feedback + comments. Trả True nếu có xóa."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT 1 FROM traces WHERE trace_id=?", (trace_id,)
            ).fetchone()
            if cur is None:
                return False
            for tbl in ("spans", "feedback", "comments", "traces"):
                self._conn.execute(f"DELETE FROM {tbl} WHERE trace_id=?", (trace_id,))
            self._conn.commit()
        return True


class JSONLExporter:
    """Appends finished span dicts as JSON lines to a file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, span_dict: dict[str, Any]) -> None:
        line = json.dumps(span_dict, ensure_ascii=False, default=str)
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
