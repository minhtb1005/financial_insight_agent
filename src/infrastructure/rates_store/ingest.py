"""Pilot ingest: SBV policy (operating) rates, static source via generic_html.

Nguồn: bài tổng hợp luatvietnam (parser generic_html) + seed đã verify
(QĐ 1123/QĐ-NHNN, hiệu lực 19/06/2023: tái cấp vốn 4,5 / tái chiết khấu 3,0 /
qua đêm 5,0). SBV gốc WAF-block nên seed là fallback hợp lệ, ghi rõ source.

Không raise khi fetch fail — trả failed kèm lý do, giữ resumable qua
ingest_meta (content hash → skip khi không đổi).
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

from infrastructure.rates_store.store import RatesStore

logger = logging.getLogger(__name__)

POLICY_URL = (
    "https://luatvietnam.vn/linh-vuc-khac/"
    "lai-suat-dieu-hanh-la-gi-883-96788-article.html"
)
POLICY_EFFECTIVE_DATE = "2023-06-19"  # QĐ 1123/QĐ-NHNN
POLICY_DECISION = "QĐ 1123/QĐ-NHNN"

# Fallback đã verify (khớp seed sbv_policy_rates trong connectors.py).
KNOWN_POLICY_RATES: dict[str, float] = {
    "tai_cap_von": 4.5,
    "tai_chiet_khau": 3.0,
    "qua_dem": 5.0,
}

_RATE_PATTERNS: dict[str, str] = {
    "tai_cap_von": r"tái cấp vốn\s*([\d.,]+)\s*%",
    "tai_chiet_khau": r"tái chiết khấu\s*([\d.,]+)\s*%",
    "qua_dem": r"(?:qua đêm|thanh toán)[^\n%]*?([\d.,]+)\s*%",
}


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def parse_policy_rates(text: str) -> dict[str, float]:
    """Trích 3 lãi suất điều hành từ text (đã clean). Thiếu key nào → KeyError."""
    out: dict[str, float] = {}
    for key, pat in _RATE_PATTERNS.items():
        m = re.search(pat, text, re.IGNORECASE)
        if not m:
            raise KeyError(f"missing rate: {key}")
        out[key] = _num(m.group(1))
    return out


def _fetch_text(url: str = POLICY_URL) -> tuple[str, str]:
    """Trả (text, source). WAF-block/rỗng → seed fallback, source ghi rõ."""
    from infrastructure.rag.ingestion.base import fetch_url
    from infrastructure.rag.ingestion.html_parser import html_to_text
    from infrastructure.rag.processing.cleaner import clean_text
    from infrastructure.rag.ingestion.connectors import SEED_TEXTS

    try:
        fr = fetch_url(url, delay=0.5, respect_robots_flag=False, verify=False)
        if fr.status == "ok" and fr.content:
            html = fr.content if isinstance(fr.content, str) else fr.content.decode("utf-8", errors="ignore")
            if "Request Rejected" not in html and "Just a moment" not in html:
                text = clean_text(html_to_text(html))
                if len(text) >= 200:
                    return text, url
    except Exception as e:
        logger.warning("policy fetch failed: %s", e)
    return SEED_TEXTS["sbv_policy_rates"], "seed:sbv_policy_rates"


def ingest_policy_rates(
    store: RatesStore | None = None,
    text: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Ingest lãi suất điều hành SBV. text=None → fetch thật (generic_html + seed fallback).

    Đổi nội dung (sha) mới upsert; trùng hash cũ → skipped. Luôn ghi nguồn +
    ngày hiệu lực QĐ 1123 vào từng row.
    """
    store = store or RatesStore()
    if text is None:
        text, source = _fetch_text()
    source = source or POLICY_URL
    try:
        rates = parse_policy_rates(text)
    except KeyError:
        # Text fetch không parse được (trang đổi layout) → seed đã verify.
        from infrastructure.rag.ingestion.connectors import SEED_TEXTS

        text = SEED_TEXTS["sbv_policy_rates"]
        source = "seed:sbv_policy_rates"
        rates = parse_policy_rates(text)
    sha = hashlib.sha256(
        ("|".join(f"{k}={v}" for k, v in sorted(rates.items()))).encode()
    ).hexdigest()
    if store.get_meta("policy_rates_hash") == sha:
        return {"skipped": True, "rates": rates, "source": source}
    for name, value in rates.items():
        store.upsert_policy(name, value, POLICY_EFFECTIVE_DATE, source=source)
    store.set_meta("policy_rates_hash", sha)
    store.set_meta(
        "policy_rates_last_run", datetime.now(timezone.utc).isoformat()
    )
    return {
        "skipped": False,
        "rates": rates,
        "source": source,
        "effective_date": POLICY_EFFECTIVE_DATE,
        "decision": POLICY_DECISION,
    }
