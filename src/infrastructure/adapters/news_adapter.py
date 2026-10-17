"""News adapter."""

from __future__ import annotations

from typing import Any

from vnstock import Company

from shared.ports.news_port import NewsPort


class NewsAdapter(NewsPort):
    def fetch_news(self, ticker: str) -> list[dict[str, Any]]:
        try:
            company = Company(symbol=ticker, source="VCI")
            df = company.news()
            if df is None or getattr(df, "empty", False):
                return []
            # Normalize VCI DataFrame rows to dicts with expected keys.
            # NOTE: VCI column names are news_title/news_short_content/
            # news_full_content/news_source(_link)/public_date — mapping the
            # wrong keys here used to yield 50 blank articles (root cause of
            # "empty news" in benchmarks).
            out: list[dict[str, Any]] = []
            for _, row in df.iterrows():
                get = row.get if hasattr(row, "get") else lambda k, d="": row[k] if k in row else d
                content = get("news_short_content", "") or get("news_full_content", "")
                out.append(
                    {
                        "title": str(get("news_title", "") or ""),
                        "content": str(content or get("news_title", "") or ""),
                        "source": str(get("news_source", "") or "VCI"),
                        "url": str(get("news_source_link", "") or ""),
                        "date": str(get("public_date", "") or ""),
                        "ticker": ticker,
                    }
                )
            return out
        except Exception:
            return []
