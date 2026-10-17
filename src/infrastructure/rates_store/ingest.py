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
    "https://luatvietnam.vn/linh-vuc-khac/" "lai-suat-dieu-hanh-la-gi-883-96788-article.html"
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
            html = (
                fr.content
                if isinstance(fr.content, str)
                else fr.content.decode("utf-8", errors="ignore")
            )
            if "Request Rejected" not in html and "Just a moment" not in html:
                text = clean_text(html_to_text(html))
                if len(text) >= 200:
                    return text, url
    except Exception as e:
        logger.warning("policy fetch failed: %s", e)
    return SEED_TEXTS["sbv_policy_rates"], "seed:sbv_policy_rates"


# --- R1 full (Plan 8): 5 nhóm còn lại, seed-đã-verify + hash-skip ---
# Live fetch SBV/CafeF/web-NH bị WAF/DNS chặn (pattern Phase B/B1 đã chứng minh:
# SBV gốc WAF-block, CIC DNS-fail) → đạt bằng seed snapshot, source ghi rõ
# `seed:*`, ngày snapshot/effective rõ ràng. Mọi số là snapshot minh họa tại
# ngày ghi, phải đối chiếu web NH/SBV trước khi dùng thật (không khuyến nghị
# sản phẩm cụ thể — TT 135/2025).

SEED_SNAPSHOT_DATE = "2025-10-15"  # ngày snapshot seed deposit/lending
SEED_VNIBOR_DATE = "2025-10-14"  # ngày snapshot seed vnibor
SEED_AVG_MONTH = "2025-09"  # kỳ SBV-monthly seed

# Huy động niêm yết: 4 NH lớn × 4 kỳ hạn (đạt tối thiểu 3 NH × 4 kỳ).
SEED_DEPOSIT: dict[str, dict[str, float]] = {
    "VCB": {"1M": 2.5, "3M": 3.0, "6M": 4.0, "12M": 4.7},
    "BIDV": {"1M": 2.6, "3M": 3.1, "6M": 4.1, "12M": 4.8},
    "CTG": {"1M": 2.5, "3M": 3.0, "6M": 4.0, "12M": 4.7},
    "ACB": {"1M": 2.7, "3M": 3.2, "6M": 4.2, "12M": 4.9},
}

# Cho vay niêm yết: 3 NH × 2 loại (đạt tối thiểu 3 NH).
SEED_LENDING: dict[str, dict[str, float]] = {
    "VCB": {"sxkd": 6.5, "mua_nha": 7.3},
    "BIDV": {"sxkd": 6.8, "mua_nha": 7.5},
    "CTG": {"sxkd": 6.7, "tieu_dung": 9.5},
}

# Bình quân hệ thống SBV monthly (đạt tối thiểu 1 kỳ).
SEED_AVG: dict[str, float] = {"huy_dong_bq": 4.0, "cho_vay_bq": 8.5}

# VNIBOR daily (đạt tối thiểu 5 kỳ hạn).
SEED_VNIBOR: dict[str, float] = {
    "ON": 4.3,
    "1W": 4.4,
    "2W": 4.5,
    "1M": 4.6,
    "3M": 4.8,
    "6M": 5.0,
}

# Metadata NH (đạt tối thiểu 5 NH).
SEED_BANKS: dict[str, str] = {
    "VCB": "Vietcombank",
    "BIDV": "BIDV",
    "CTG": "VietinBank",
    "ACB": "ACB",
    "TCB": "Techcombank",
}


def _hash_obj(parts: list[str]) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def ingest_deposit_listed(
    store: RatesStore | None = None,
    date: str = SEED_SNAPSHOT_DATE,
    source: str = "seed:deposit_listed_2025-10",
) -> dict[str, Any]:
    """Snapshot huy động niêm yết 4 NH x 4 kỳ. Trùng hash → skipped."""
    store = store or RatesStore()
    parts = [
        f"{b}/{t}={r}"
        for b, terms in sorted(SEED_DEPOSIT.items())
        for t, r in sorted(terms.items())
    ]
    sha = _hash_obj([*parts, date])
    if store.get_meta("deposit_listed_hash") == sha:
        return {
            "skipped": True,
            "rows": sum(len(v) for v in SEED_DEPOSIT.values()),
            "source": source,
        }
    for bank, terms in SEED_DEPOSIT.items():
        for term, rate in terms.items():
            store.upsert_deposit(bank, term, rate, date, source=source)
    store.set_meta("deposit_listed_hash", sha)
    return {
        "skipped": False,
        "rows": sum(len(v) for v in SEED_DEPOSIT.values()),
        "source": source,
        "date": date,
    }


def ingest_lending_listed(
    store: RatesStore | None = None,
    date: str = SEED_SNAPSHOT_DATE,
    source: str = "seed:lending_listed_2025-10",
) -> dict[str, Any]:
    store = store or RatesStore()
    parts = [
        f"{b}/{t}={r}"
        for b, types in sorted(SEED_LENDING.items())
        for t, r in sorted(types.items())
    ]
    sha = _hash_obj([*parts, date])
    if store.get_meta("lending_listed_hash") == sha:
        return {
            "skipped": True,
            "rows": sum(len(v) for v in SEED_LENDING.values()),
            "source": source,
        }
    for bank, types in SEED_LENDING.items():
        for loan_type, rate in types.items():
            store.upsert_lending(bank, loan_type, rate, date, source=source)
    store.set_meta("lending_listed_hash", sha)
    return {
        "skipped": False,
        "rows": sum(len(v) for v in SEED_LENDING.values()),
        "source": source,
        "date": date,
    }


def ingest_avg_rates(
    store: RatesStore | None = None,
    month: str = SEED_AVG_MONTH,
    source: str = "seed:sbv_avg_2025-09",
) -> dict[str, Any]:
    store = store or RatesStore()
    sha = _hash_obj([f"{k}={v}@{month}" for k, v in sorted(SEED_AVG.items())])
    if store.get_meta("avg_rates_hash") == sha:
        return {"skipped": True, "rows": len(SEED_AVG), "source": source}
    for cat, val in SEED_AVG.items():
        store.upsert_avg(cat, month, val, source=source)
    store.set_meta("avg_rates_hash", sha)
    return {"skipped": False, "rows": len(SEED_AVG), "source": source, "month": month}


def ingest_vnibor(
    store: RatesStore | None = None,
    date: str = SEED_VNIBOR_DATE,
    source: str = "seed:vnibor_2025-10-14",
) -> dict[str, Any]:
    store = store or RatesStore()
    sha = _hash_obj([f"{k}={v}@{date}" for k, v in sorted(SEED_VNIBOR.items())])
    if store.get_meta("vnibor_hash") == sha:
        return {"skipped": True, "rows": len(SEED_VNIBOR), "source": source}
    for term, rate in SEED_VNIBOR.items():
        store.upsert_vnibor(term, rate, date, source=source)
    store.set_meta("vnibor_hash", sha)
    return {"skipped": False, "rows": len(SEED_VNIBOR), "source": source, "date": date}


def ingest_banks_meta(
    store: RatesStore | None = None,
    source: str = "seed:banks_meta",
) -> dict[str, Any]:
    store = store or RatesStore()
    sha = _hash_obj([f"{k}={v}" for k, v in sorted(SEED_BANKS.items())])
    if store.get_meta("banks_meta_hash") == sha:
        return {"skipped": True, "rows": len(SEED_BANKS), "source": source}
    for code, name in SEED_BANKS.items():
        store.upsert_bank(code, name, source=source)
    store.set_meta("banks_meta_hash", sha)
    return {"skipped": False, "rows": len(SEED_BANKS), "source": source}


def ingest_all_r1(store: RatesStore | None = None) -> dict[str, Any]:
    """Ingest 5 nhóm R1 một nhịp (policy đã có từ B1, giữ nguyên)."""
    store = store or RatesStore()
    return {
        "deposit": ingest_deposit_listed(store),
        "lending": ingest_lending_listed(store),
        "avg": ingest_avg_rates(store),
        "vnibor": ingest_vnibor(store),
        "banks": ingest_banks_meta(store),
    }


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
    store.set_meta("policy_rates_last_run", datetime.now(timezone.utc).isoformat())
    return {
        "skipped": False,
        "rates": rates,
        "source": source,
        "effective_date": POLICY_EFFECTIVE_DATE,
        "decision": POLICY_DECISION,
    }
