"""Unit tests for pure sentiment helpers in news_sentiment_service.

Covers _classify_sentiment (incl. negation handling) and
_calc_sentiment_from_articles aggregation. No network, no model weights.
"""

import pytest

from application.services.portfolio.news_sentiment_service import (
    _calc_sentiment_from_articles,
    _classify_sentiment,
)


@pytest.mark.unit
class TestClassifySentiment:
    def test_empty_text_returns_zero(self):
        assert _classify_sentiment("") == 0.0

    def test_positive_text(self):
        assert _classify_sentiment("Lợi nhuận tăng trưởng mạnh, triển vọng khả quan") > 0

    def test_negative_text(self):
        assert _classify_sentiment("Lỗ nặng, rủi ro phá sản, cảnh báo khó khăn") < 0

    def test_neutral_text_returns_zero(self):
        assert _classify_sentiment("Hôm nay là thứ năm, thị trường mở cửa bình thường") == 0.0

    def test_negated_positive_flips_to_negative(self):
        assert _classify_sentiment("Lợi nhuận không tăng trưởng") < 0

    def test_negated_negative_flips_to_positive(self):
        assert _classify_sentiment("Không có rủi ro, không lỗ") > 0

    def test_score_bounded(self):
        for text in ["lãi lãi lãi tăng tăng tăng", "lỗ lỗ lỗ giảm giảm giảm"]:
            assert -1.0 <= _classify_sentiment(text) <= 1.0


@pytest.mark.unit
class TestCalcSentimentFromArticles:
    def test_empty_articles_returns_zero(self):
        assert _calc_sentiment_from_articles([]) == 0.0

    def test_title_weighted_over_content(self):
        articles = [{"title": "Lợi nhuận tăng trưởng mạnh", "content": "Hôm nay trời đẹp"}]
        assert _calc_sentiment_from_articles(articles) > 0

    def test_mixed_articles_average(self):
        articles = [
            {"title": "Lợi nhuận tăng trưởng", "content": ""},
            {"title": "Thua lỗ nặng nề", "content": ""},
        ]
        score = _calc_sentiment_from_articles(articles)
        assert -0.5 < score < 0.5

    def test_missing_keys_do_not_crash(self):
        assert _calc_sentiment_from_articles([{}]) == 0.0
