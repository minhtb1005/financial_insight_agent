"""Unit tests for sentiment engines dispatcher + RSS adapter mapping.

LLM/HF heavies are mocked — real-model quality is measured by
evals/run_news_sentiment_eval.py on the 45-label golden set, not here.
"""

from unittest.mock import MagicMock, patch

from infrastructure.sentiment.engines import (
    classify_article,
    classify_hf,
    classify_keyword,
)


class TestClassifyKeyword:
    def test_sign_mapping(self):
        assert classify_keyword(0.5)["label"] == "pos"
        assert classify_keyword(-0.25)["label"] == "neg"
        assert classify_keyword(0.0)["label"] == "neu"

    def test_shape(self):
        v = classify_keyword(0.5)
        assert set(v) == {"label", "score", "rationale", "engine"}
        assert v["engine"] == "keyword"
        assert -1.0 <= v["score"] <= 1.0


class TestClassifyHf:
    def test_signed_score_mapping(self):
        # NOTE: patching transformers.pipeline does not intercept its lazy
        # loader, so inject the loaded pipe directly (mapping logic is what
        # we test here; real-model quality is measured by the eval script).
        import infrastructure.sentiment.engines as eng

        preds = [
            {"label": "Bearish", "score": 0.8},
            {"label": "Uncertainty", "score": 0.15},
            {"label": "Bullish", "score": 0.05},
        ]
        eng._hf_pipe = lambda text: [preds]  # noqa: E731 (test double)
        try:
            v = classify_hf("T", "x")
        finally:
            eng._hf_pipe = None
        assert v["label"] == "neg" and v["score"] == -0.8 and v["engine"] == "hf"
        assert "Bearish" in v["rationale"]


class TestClassifyArticleDispatcher:
    def test_llm_engine_used(self):
        with patch(
            "infrastructure.sentiment.engines.classify_llm",
            return_value={"label": "pos", "score": 0.9, "rationale": "r", "engine": "llm"},
        ):
            v = classify_article("T", "x", engine="llm")
        assert v["engine"] == "llm" and v["label"] == "pos"

    def test_llm_failure_falls_back_keyword(self):
        with patch(
            "infrastructure.sentiment.engines.classify_llm",
            side_effect=RuntimeError("down"),
        ):
            v = classify_article("T", "x", engine="llm", keyword_score=-0.5)
        assert v == classify_keyword(-0.5)

    def test_unknown_engine_falls_back(self):
        v = classify_article("T", "x", engine="nope", keyword_score=0.3)
        assert v["engine"] == "keyword" and v["label"] == "pos"


class TestRssAdapterMapping:
    def test_fetch_filters_by_ticker_and_maps_fields(self):
        from infrastructure.adapters.rss_news_adapter import RssNewsAdapter

        entry_vcb = MagicMock()
        entry_vcb.title = "VCB vượt đỉnh lịch sử"
        entry_vcb.summary = "Cổ phiếu VCB tăng mạnh"
        entry_vcb.link = "https://cafef.vn/a"
        entry_vcb.published = "Wed, 10 Sep 2026 08:00:00 +0700"
        entry_other = MagicMock()
        entry_other.title = "Giá vàng hôm nay"
        entry_other.summary = "Vàng SJC đi ngang"
        entry_other.link = "https://cafef.vn/b"

        feed = MagicMock()
        feed.entries = [entry_vcb, entry_other]
        with patch("feedparser.parse", return_value=feed), patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.content = b"<rss></rss>"
            arts = RssNewsAdapter().fetch_news("VCB")
        assert len(arts) == 1
        a = arts[0]
        assert a["ticker"] == "VCB" and a["source"] == "CafeF"
        assert set(a) == {"title", "content", "source", "url", "date", "ticker"}
        assert "2026-09-10" in a["date"]

    def test_empty_ticker_and_fallback(self):
        from infrastructure.adapters.rss_news_adapter import RssNewsAdapter

        assert RssNewsAdapter().fetch_news("") == []
        fb = MagicMock()
        fb.fetch_news.return_value = [{"title": "t"}]
        with (
            patch("feedparser.parse", side_effect=Exception("net down")),
            patch("requests.get", side_effect=Exception("net down")),
        ):
            assert RssNewsAdapter(fallback=fb).fetch_news("VCB") == [{"title": "t"}]

    def test_alias_matching(self):
        from infrastructure.adapters.rss_news_adapter import _mentions

        assert _mentions("Vietcombank báo lãi", "VCB") is True
        assert _mentions("Giá vàng hôm nay", "VCB") is False


class TestVciMapping:
    def test_vci_columns_mapped(self):
        import pandas as pd

        from infrastructure.adapters.news_adapter import NewsAdapter

        df = pd.DataFrame(
            [
                {
                    "news_title": "VCB: Thông báo chi nhánh",
                    "news_short_content": None,
                    "news_full_content": None,
                    "news_source": None,
                    "news_source_link": None,
                    "public_date": "2026-09-07T17:14:35",
                }
            ]
        )
        with patch("infrastructure.adapters.news_adapter.Company") as mock_company:
            mock_company.return_value.news.return_value = df
            arts = NewsAdapter().fetch_news("VCB")
        assert len(arts) == 1
        assert arts[0]["title"] == "VCB: Thông báo chi nhánh"
        assert arts[0]["date"] == "2026-09-07T17:14:35"
        assert arts[0]["ticker"] == "VCB"


class TestCombinedNewsAdapter:
    def test_merge_and_dedupe_and_drop_blank(self):
        from infrastructure.adapters.rss_news_adapter import CombinedNewsAdapter

        primary = MagicMock()
        primary.fetch_news.return_value = [
            {"title": "VCB lãi lớn", "content": "", "ticker": "VCB"},
            {"title": "", "content": "", "ticker": "VCB"},  # blank -> dropped
        ]
        secondary = MagicMock()
        secondary.fetch_news.return_value = [
            {"title": "VCB lãi lớn", "content": "excerpt", "ticker": "VCB"},  # dup
            {"title": "VCB chia cổ tức", "content": "ex", "ticker": "VCB"},
        ]
        out = CombinedNewsAdapter(primary, secondary).fetch_news("VCB")
        assert [a["title"] for a in out] == ["VCB lãi lớn", "VCB chia cổ tức"]

    def test_secondary_failure_tolerated(self):
        from infrastructure.adapters.rss_news_adapter import CombinedNewsAdapter

        primary = MagicMock()
        primary.fetch_news.return_value = [{"title": "t", "content": "c"}]
        bad = MagicMock()
        bad.fetch_news.side_effect = RuntimeError("down")
        out = CombinedNewsAdapter(primary, bad).fetch_news("VCB")
        assert len(out) == 1
