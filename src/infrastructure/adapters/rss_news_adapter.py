"""RSS news adapter (Phase 3) — pure-RSS crawl, no paid dependency.

Chose over ``vnnews`` (unmaintained, install fails) and ``vnewsapi`` (stale
hard-coded URLs, unbounded sitemap crawl) per ``docs/news_source_spike.md``.
Feed URLs below were verified live (50 entries each); only title + excerpt +
link + date are stored (copyright).
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any

from shared.ports.news_port import NewsPort

logger = logging.getLogger(__name__)

# Verified live (each returns ~50 entries with title/link/published/summary).
SITE_FEEDS: tuple[tuple[str, str], ...] = (
    ("CafeF", "https://cafef.vn/thi-truong-chung-khoan.rss"),
    ("CafeF", "https://cafef.vn/tai-chinh-ngan-hang.rss"),
    ("CafeF", "https://cafef.vn/doanh-nghiep.rss"),
    ("CafeF", "https://cafef.vn/vi-mo-dau-tu.rss"),
)

_MAX_ENTRIES_PER_FEED = 15
_EXCERPT_CHARS = 500
_REQUEST_TIMEOUT_S = 20
_USER_AGENT = "Mozilla/5.0 (compatible; finsight-news/1.0)"

# Company-name aliases boost RSS recall (tickers alone rarely appear in
# headlines). Pilot tickers only — extend as coverage grows.
TICKER_ALIASES: dict[str, tuple[str, ...]] = {
    "VCB": ("Vietcombank", "Ngoại thương"),
    "HPG": ("Hòa Phát", "Hoa Phat"),
    "FPT": ("FPT",),
    "VNM": ("Vinamilk",),
    "MWG": ("Thế Giới Di Động", "The Gioi Di Dong"),
    "BID": ("BIDV",),
    "TCB": ("Techcombank",),
    "VIC": ("Vingroup", "Vinhomes"),
    "MSN": ("Masan",),
    "CTG": ("VietinBank", "Vietinbank"),
    "GAS": ("PV Gas", "PV GAS"),
    "MBB": ("MB Bank", "MBBank", "Quân đội"),
    "VHM": ("Vinhomes",),
    "PLX": ("Petrolimex",),
    "HSG": ("Hoa Sen",),
}

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str, limit: int = _EXCERPT_CHARS) -> str:
    text = html.unescape(_TAG_RE.sub(" ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _mentions(text: str, ticker: str) -> bool:
    candidates = (ticker, *TICKER_ALIASES.get(ticker.upper(), ()))
    return any(
        re.search(rf"\b{re.escape(alias)}\b", text or "", re.IGNORECASE) for alias in candidates
    )


class RssNewsAdapter(NewsPort):
    """Fetch ticker news from verified RSS feeds, optional fallback port."""

    def __init__(
        self,
        feeds: tuple[tuple[str, str], ...] = SITE_FEEDS,
        fallback: NewsPort | None = None,
    ) -> None:
        self._feeds = feeds
        self._fallback = fallback

    def fetch_news(self, ticker: str) -> list[dict[str, Any]]:
        ticker = (ticker or "").upper()
        if not ticker:
            return []
        articles = self._fetch_rss(ticker)
        if not articles and self._fallback is not None:
            try:
                articles = self._fallback.fetch_news(ticker) or []
            except Exception as e:
                logger.warning("News fallback failed for %s: %s", ticker, e)
        return articles

    def _fetch_rss(self, ticker: str) -> list[dict[str, Any]]:
        try:
            import feedparser
            import requests
        except ImportError as e:
            logger.warning("RSS deps missing: %s", e)
            return []
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for site, url in self._feeds:
            try:
                resp = requests.get(
                    url, timeout=_REQUEST_TIMEOUT_S, headers={"User-Agent": _USER_AGENT}
                )
                if resp.status_code != 200:
                    continue
                feed = feedparser.parse(resp.content)
            except Exception as e:
                logger.warning("RSS feed failed %s: %s", url, e)
                continue
            for entry in feed.entries[:_MAX_ENTRIES_PER_FEED]:
                title = _clean(getattr(entry, "title", ""), 300)
                summary = _clean(getattr(entry, "summary", getattr(entry, "description", "")))
                if not (_mentions(title, ticker) or _mentions(summary, ticker)):
                    continue
                link = getattr(entry, "link", "")
                if link in seen:
                    continue
                seen.add(link)
                published = getattr(entry, "published", "") or getattr(entry, "updated", "")
                out.append(
                    {
                        "title": title,
                        "content": summary,  # excerpt only (copyright)
                        "source": site,
                        "url": link,
                        "date": _to_iso(published),
                        "ticker": ticker,
                    }
                )
        return out


def _to_iso(value: str) -> str:
    if not value:
        return ""
    try:
        import email.utils

        dt = email.utils.parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except (TypeError, ValueError):
        return value


def _norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").lower()).strip()


class CombinedNewsAdapter(NewsPort):
    """Merge primary + secondary sources, deduped by normalized title.

    Used as VCI-fixed (coverage: ~50 titled articles/ticker) + RSS (excerpts).
    Blank articles (no title and no content) are dropped — they carry no signal.
    """

    def __init__(
        self, primary: NewsPort, secondary: NewsPort | None = None, max_articles: int = 60
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._max = max_articles

    def fetch_news(self, ticker: str) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []
        for port in (self._primary, self._secondary):
            if port is None:
                continue
            try:
                articles.extend(port.fetch_news(ticker) or [])
            except Exception as e:
                logger.warning("News source failed for %s: %s", ticker, e)
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for a in articles:
            if not isinstance(a, dict):
                continue
            title, content = a.get("title", "") or "", a.get("content", "") or ""
            if not title.strip() and not content.strip():
                continue  # blank article — no signal
            key = _norm_title(title) or _norm_title(content[:120])
            if key in seen:
                continue
            seen.add(key)
            out.append(a)
            if len(out) >= self._max:
                break
        return out
