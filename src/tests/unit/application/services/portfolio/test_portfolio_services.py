"""Unit tests for portfolio services — news sentiment and portfolio manager."""

from unittest.mock import patch, MagicMock
import os
import json
import tempfile

from application.services.portfolio.portfolio_service import PortfolioService
from application.services.portfolio.news_sentiment_service import NewsSentimentService
from shared.ports.market_data_port import MarketDataPort
from shared.ports.news_port import NewsPort
from shared.service_registry import set_service


class FakeCache:
    def __init__(self, store=None):
        self._store = store or {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ttl_hours=1.0):
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)


class FakeMarketData(MarketDataPort):
    def __init__(self, rows):
        self._rows = rows

    def get_price_data(self, ticker, start_date, end_date, interval="1d"):
        return {
            "ticker": ticker,
            "data": self._rows,
            "start_date": start_date,
            "end_date": end_date,
            "data_as_of": "2026-03-10T00:00:00+00:00",
            "source": "db",
        }


class FakeNewsPort(NewsPort):
    def __init__(self, articles):
        self._articles = articles

    def fetch_news(self, ticker):
        return self._articles


def _price_rows(closes):
    return [
        {
            "date": f"2026-03-{10 + i:02d}",
            "open": c - 1.0,
            "high": c + 1.0,
            "low": c - 1.0,
            "close": c,
            "volume": 1000,
        }
        for i, c in enumerate(closes)
    ]


# -- handle_news_sentiment_query ------------------------------------------


def test_news_sentiment_empty_tickers_returns_error():
    svc = NewsSentimentService(cache=FakeCache(), news_port=FakeNewsPort([]))

    result = svc.handle_query(tickers=[], field="news")
    assert "error" in result


def test_news_sentiment_valid_ticker():
    svc = NewsSentimentService(
        cache=FakeCache(),
        news_port=FakeNewsPort(
            [
                {
                    "title": "VCB kinh doanh kỷ lục",
                    "content": "Lợi nhuận tăng mạnh",
                    "source": "VnEconomy",
                    "url": "https://example.com",
                    "date": "2026-03-01",
                    "ticker": "VCB",
                }
            ]
        ),
    )

    result = svc.handle_query(tickers=["VCB"], field="news")
    assert "news" in result
    assert len(result["news"]["VCB"]) == 1
    assert result["news"]["VCB"][0]["title"] == "VCB kinh doanh kỷ lục"


# -- _negation_in_prefix / _is_negated (pure) -----------------------------


def test_negation_in_prefix_no_negation():
    from application.services.portfolio.news_sentiment_service import _negation_in_prefix

    assert _negation_in_prefix(["lợi", "nhuận"]) is False


def test_negation_in_prefix_with_negation():
    from application.services.portfolio.news_sentiment_service import _negation_in_prefix

    assert _negation_in_prefix(["không", "có"]) is True


def test_negation_in_prefix_english():
    from application.services.portfolio.news_sentiment_service import _negation_in_prefix

    assert _negation_in_prefix(["not", "good"]) is True


def test_is_negated_within_window():
    from application.services.portfolio.news_sentiment_service import _is_negated

    assert _is_negated("tăng", "công ty không tăng trưởng") is True


def test_is_negated_outside_window():
    from application.services.portfolio.news_sentiment_service import _is_negated

    assert _is_negated("tăng", "hôm qua trời mưa rất to hôm nay tăng") is False


# -- PortfolioManager -----------------------------------------------------


def test_portfolio_manager_load_nonexistent():
    from application.services.portfolio.portfolio_service import PortfolioManager

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    os.unlink(path)
    pm = PortfolioManager(portfolio_file=path)
    assert pm.portfolio == {"holdings": {}, "transactions": []}


def test_portfolio_manager_add_holding():
    from application.services.portfolio.portfolio_service import PortfolioManager

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"holdings": {}, "transactions": []}, f)
        path = f.name
    pm = PortfolioManager(portfolio_file=path)
    pm.add_holding("VCB", 10, 100.0)
    assert pm.portfolio["holdings"]["VCB"] == 10
    assert len(pm.portfolio["transactions"]) == 1
    os.unlink(path)


def test_portfolio_manager_add_holding_existing():
    from application.services.portfolio.portfolio_service import PortfolioManager

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"holdings": {"VCB": 5}, "transactions": []}, f)
        path = f.name
    pm = PortfolioManager(portfolio_file=path)
    pm.add_holding("VCB", 10, 100.0)
    assert pm.portfolio["holdings"]["VCB"] == 15
    os.unlink(path)


def test_portfolio_manager_save_and_reload():
    from application.services.portfolio.portfolio_service import PortfolioManager

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"holdings": {}, "transactions": []}, f)
        path = f.name
    pm1 = PortfolioManager(portfolio_file=path)
    pm1.add_holding("HPG", 50, 25.0)
    pm1.save_portfolio()
    pm2 = PortfolioManager(portfolio_file=path)
    assert pm2.portfolio["holdings"]["HPG"] == 50
    os.unlink(path)


def test_portfolio_manager_corrupted_file():
    from application.services.portfolio.portfolio_service import PortfolioManager

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json")
        path = f.name
    pm = PortfolioManager(portfolio_file=path)
    assert pm.portfolio == {"holdings": {}, "transactions": []}
    os.unlink(path)


def test_portfolio_manager_thread_lock_present():
    from application.services.portfolio.portfolio_service import PortfolioManager

    pm = PortfolioManager()
    assert hasattr(pm, "_file_lock")
    assert hasattr(pm, "portfolio")


# -- PortfolioService._fetch_price -----------------------------------------


def _make_portfolio_service(cache=None, rows=None):
    return PortfolioService(
        cache=cache if cache is not None else FakeCache(),
        market_data=FakeMarketData(rows if rows is not None else []),
        company_port=MagicMock(),
    )


def test_fetch_price_cache_hit():
    mock_cache = MagicMock()
    mock_cache.get.return_value = 105.0
    svc = _make_portfolio_service(cache=mock_cache)
    result = svc._fetch_price("VCB", 10, "2026-03-10")
    assert result["ticker"] == "VCB"
    assert result["current_price"] == 105.0
    assert result["value"] == 1050.0
    mock_cache.set.assert_not_called()


def test_fetch_price_cache_miss():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    svc = _make_portfolio_service(cache=mock_cache, rows=_price_rows([100.0, 102.0]))
    result = svc._fetch_price("VCB", 5, "2026-03-10")
    assert result["ticker"] == "VCB"
    assert result["current_price"] == 102.0
    assert result["value"] == 510.0
    mock_cache.set.assert_called_once()


def test_fetch_price_empty_data():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    svc = _make_portfolio_service(cache=mock_cache, rows=[])
    result = svc._fetch_price("VCB", 5, "2026-03-10")
    assert "error" in result


def test_fetch_price_client_exception():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_md = MagicMock(spec=MarketDataPort)
    mock_md.get_price_data.side_effect = ValueError("API error")
    svc = PortfolioService(cache=mock_cache, market_data=mock_md, company_port=MagicMock())
    result = svc._fetch_price("VCB", 5, "2026-03-10")
    assert "error" in result


# -- PortfolioService._fetch_sector_and_price -------------------------------


def test_fetch_sector_and_price_cache_hit():
    mock_cache = MagicMock()
    mock_cache.get.return_value = 105.0
    svc = _make_portfolio_service(cache=mock_cache)
    result = svc._fetch_sector_and_price("VCB", 10, "2026-03-10")
    assert result["ticker"] == "VCB"
    assert result["value"] == 1050.0


def test_fetch_sector_and_price_missing_sector():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    svc = _make_portfolio_service(cache=mock_cache, rows=_price_rows([100.0]))
    result = svc._fetch_sector_and_price("VCB", 10, "2026-03-10")
    assert result["ticker"] == "VCB"
    assert result["sector"] == "Unknown"
    assert result["value"] == 1000.0


# -- PortfolioService.get_portfolio_value -----------------------------------


@patch.object(PortfolioService, "_fetch_price")
def test_get_portfolio_value_with_holdings(mock_fetch):
    mock_fetch.return_value = {
        "ticker": "VCB",
        "quantity": 10,
        "current_price": 100.0,
        "value": 1000.0,
    }
    svc = _make_portfolio_service()
    with patch("application.services.portfolio.portfolio_service.PortfolioManager") as mock_pm:
        mock_pm.return_value.get_holdings.return_value = {"VCB": 10}
        mock_pm.return_value.portfolio = {"holdings": {"VCB": 10}, "transactions": []}
        result = svc.get_portfolio_value({})
    assert result["portfolio_value"] == 1000.0
    assert "VCB" in result["holdings"]


@patch.object(PortfolioService, "_fetch_price")
def test_get_portfolio_value_empty_holdings(mock_fetch):
    svc = _make_portfolio_service()
    with patch("application.services.portfolio.portfolio_service.PortfolioManager") as mock_pm:
        mock_pm.return_value.get_holdings.return_value = {}
        mock_pm.return_value.portfolio = {"holdings": {}, "transactions": []}
        result = svc.get_portfolio_value({})
    assert result["portfolio_value"] == 0
    assert result["holdings"] == {}


@patch.object(PortfolioService, "_fetch_price")
def test_get_portfolio_value_skips_error_tickers(mock_fetch):
    def fetch_side(ticker, *_a, **_kw):
        if ticker == "VCB":
            return {"ticker": "VCB", "quantity": 10, "current_price": 100.0, "value": 1000.0}
        return {"error": "not found"}

    mock_fetch.side_effect = fetch_side
    svc = _make_portfolio_service()
    with patch("application.services.portfolio.portfolio_service.PortfolioManager") as mock_pm:
        mock_pm.return_value.get_holdings.return_value = {"VCB": 10, "BAD": 5}
        mock_pm.return_value.portfolio = {"holdings": {"VCB": 10, "BAD": 5}, "transactions": []}
        result = svc.get_portfolio_value({})
    assert result["portfolio_value"] == 1000.0
    assert "VCB" in result["holdings"]


# -- PortfolioService.get_portfolio_performance -----------------------------


@patch(
    "application.services.portfolio.portfolio_service.PortfolioManager.get_transactions",
    return_value=[
        {"type": "buy", "quantity": 10, "price": 100.0},
        {"type": "sell", "quantity": 2, "price": 110.0},
    ],
)
@patch.object(PortfolioService, "get_portfolio_value")
def test_get_portfolio_performance_with_transactions(mock_get_value, mock_txns):
    mock_get_value.return_value = {"portfolio_value": 1200.0}
    svc = _make_portfolio_service()
    result = svc.get_portfolio_performance({})
    assert result["total_cost"] == 1000.0
    assert result["total_proceeds"] == 220.0
    assert result["total_return"] == 420.0


@patch(
    "application.services.portfolio.portfolio_service.PortfolioManager.get_transactions",
    return_value=[],
)
@patch.object(PortfolioService, "get_portfolio_value")
def test_get_portfolio_performance_no_transactions(mock_get_value, mock_txns):
    svc = _make_portfolio_service()
    result = svc.get_portfolio_performance({})
    assert "total_return" in result
    assert result["total_return"] == 0


@patch(
    "application.services.portfolio.portfolio_service.PortfolioManager.get_transactions",
    return_value=[{"type": "sell", "quantity": 1, "price": 100.0}],
)
@patch.object(PortfolioService, "get_portfolio_value")
def test_get_portfolio_performance_zero_cost(mock_get_value, mock_txns):
    mock_get_value.return_value = {"portfolio_value": 100.0}
    svc = _make_portfolio_service()
    result = svc.get_portfolio_performance({})
    assert result["total_cost"] == 0
    assert result["return_rate"] == 0


# -- PortfolioService.get_portfolio_allocation ------------------------------


@patch.object(PortfolioService, "_fetch_sector_and_price")
def test_get_portfolio_allocation_multiple_sectors(mock_fetch):
    def side_effect(ticker, qty, *_a, **_kw):
        data = {
            "VCB": {"ticker": "VCB", "sector": "banking", "value": 600.0},
            "VNM": {"ticker": "VNM", "sector": "food", "value": 400.0},
        }
        return data.get(ticker, {"error": "not found"})

    mock_fetch.side_effect = side_effect
    svc = _make_portfolio_service()
    with patch("application.services.portfolio.portfolio_service.PortfolioManager") as mock_pm:
        mock_pm.return_value.get_holdings.return_value = {"VCB": 10, "VNM": 5}
        mock_pm.return_value.portfolio = {"holdings": {"VCB": 10, "VNM": 5}, "transactions": []}
        result = svc.get_portfolio_allocation({})
    assert "allocation" in result
    assert result["diversification_score"] == 50
    assert result["total_value"] == 1000.0


def test_get_portfolio_allocation_empty():
    svc = _make_portfolio_service()
    with patch("application.services.portfolio.portfolio_service.PortfolioManager") as mock_pm:
        mock_pm.return_value.get_holdings.return_value = {}
        mock_pm.return_value.portfolio = {"holdings": {}, "transactions": []}
        result = svc.get_portfolio_allocation({})
    assert result["diversification_score"] == 0
    assert result["allocation"] == {}


@patch.object(PortfolioService, "_fetch_sector_and_price")
def test_get_portfolio_allocation_single_sector(mock_fetch):
    mock_fetch.return_value = {"ticker": "VCB", "sector": "banking", "value": 1000.0}
    svc = _make_portfolio_service()
    with patch("application.services.portfolio.portfolio_service.PortfolioManager") as mock_pm:
        mock_pm.return_value.get_holdings.return_value = {"VCB": 10}
        mock_pm.return_value.portfolio = {"holdings": {"VCB": 10}, "transactions": []}
        result = svc.get_portfolio_allocation({})
    assert result["diversification_score"] == 20


# -- PortfolioService._update_portfolio_data --------------------------------


def test_update_portfolio_new_ticker():
    svc = _make_portfolio_service()
    with patch("application.services.portfolio.portfolio_service.PortfolioManager") as mock_pm:
        mock_pm.return_value.get_holdings.return_value = {}
        mock_pm.return_value.portfolio = {"holdings": {}, "transactions": []}
        svc._update_portfolio_data({"VCB": 10})
    mock_pm.return_value.add_holding.assert_called_once_with(ticker="VCB", quantity=10, price=0.0)


def test_update_portfolio_existing_ticker():
    svc = _make_portfolio_service()
    with patch("application.services.portfolio.portfolio_service.PortfolioManager") as mock_pm:
        mock_pm.return_value.get_holdings.return_value = {"VCB": 5}
        mock_pm.return_value.portfolio = {"holdings": {"VCB": 5}, "transactions": []}
        svc._update_portfolio_data({"VCB": 10})
    mock_pm.return_value.add_holding.assert_called_once_with(ticker="VCB", quantity=10, price=0.0)


# -- PortfolioService.handle_query ------------------------------------------


@patch.object(PortfolioService, "get_portfolio_value")
def test_handle_query_portfolio_value(mock_get_value):
    mock_get_value.return_value = {"portfolio_value": 1000.0}
    svc = _make_portfolio_service()
    result = svc.handle_query(requested_field="portfolio_value")
    assert result["portfolio_value"] == 1000.0


@patch.object(PortfolioService, "get_portfolio_performance")
def test_handle_query_portfolio_performance(mock_get_perf):
    mock_get_perf.return_value = {"total_return": 200.0}
    svc = _make_portfolio_service()
    result = svc.handle_query(requested_field="portfolio_performance")
    assert result["total_return"] == 200.0


@patch.object(PortfolioService, "get_portfolio_value")
@patch.object(PortfolioService, "get_portfolio_performance")
@patch.object(PortfolioService, "get_portfolio_allocation")
def test_handle_query_portfolio_allocation(mock_alloc, mock_perf, mock_value):
    mock_value.return_value = {"portfolio_value": 1000.0}
    mock_perf.return_value = {"total_return": 100.0}
    mock_alloc.return_value = {"allocation": {"banking": 1000}}
    svc = _make_portfolio_service()
    result = svc.handle_query(requested_field="portfolio_allocation")
    assert "portfolio_value" in result
    assert "portfolio_performance" in result
    assert "portfolio_allocation" in result


@patch.object(PortfolioService, "get_portfolio_value")
def test_handle_query_with_portfolio_data(mock_get_value):
    mock_get_value.return_value = {"portfolio_value": 1000.0}
    svc = _make_portfolio_service()
    with patch.object(svc, "_update_portfolio_data") as mock_update:
        result = svc.handle_query(requested_field="portfolio_value", portfolio={"VCB": 10})
    mock_update.assert_called_once_with({"VCB": 10})
    assert result["portfolio_value"] == 1000.0


# -- handle_portfolio_query module-level ------------------------------------


@patch(
    "application.services.portfolio.portfolio_service.handle_portfolio_query",
    side_effect=lambda **kw: {"result": "ok"},
)
def test_handle_portfolio_query_module(mock_h):
    from application.services.portfolio.portfolio_service import handle_portfolio_query

    result = handle_portfolio_query(field="portfolio_value")
    assert result is not None


# -- NewsSentimentService internal methods ---------------------------------


def _make_news_service(articles=None, cache=None):
    from application.services.portfolio.news_sentiment_service import NewsSentimentService

    return NewsSentimentService(
        cache=cache if cache is not None else FakeCache(),
        news_port=FakeNewsPort(articles if articles is not None else []),
    )


def test_filter_articles_by_days():
    from datetime import datetime, timezone

    svc = _make_news_service()
    articles = [
        {"title": "old", "date": "2026-04-01"},
        {"title": "recent", "date": "2026-05-17"},
    ]
    with patch("application.services.portfolio.news_sentiment_service.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = svc._filter_articles_by_time(articles, {"days": 7})
    assert len(result) == 1
    assert result[0]["title"] == "recent"


def test_filter_articles_no_time_params():
    svc = _make_news_service()
    articles = [{"title": "a", "date": "2026-01-01"}]
    result = svc._filter_articles_by_time(articles, {})
    assert len(result) == 1


def test_filter_articles_invalid_date():
    svc = _make_news_service()
    articles = [{"title": "bad date", "date": "not-a-date"}]
    result = svc._filter_articles_by_time(articles, {"days": 7})
    assert len(result) == 1


def test_filter_articles_empty_date():
    svc = _make_news_service()
    articles = [{"title": "empty date", "date": ""}]
    result = svc._filter_articles_by_time(articles, {"days": 7})
    assert len(result) == 1


def test_fetch_single_news_cache_hit():
    mock_cache = MagicMock()
    mock_cache.get.return_value = [{"title": "cached news"}]
    svc = _make_news_service(cache=mock_cache)
    result = svc._fetch_single_news("VCB")
    assert result[0]["title"] == "cached news"


def test_fetch_single_news_fetch_empty():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    svc = _make_news_service(cache=mock_cache, articles=[])
    result = svc._fetch_single_news("VCB")
    assert result == []


def test_get_news_data_no_tickers():
    svc = _make_news_service()
    result = svc.get_news_data({"tickers": []})
    assert "note" in result
    assert result["news"] == {}


@patch.object(NewsSentimentService, "_fetch_single_news")
@patch.object(NewsSentimentService, "_filter_articles_by_time")
def test_get_news_data_with_tickers(mock_filter, mock_fetch):
    mock_fetch.return_value = [{"title": "news1"}]
    mock_filter.return_value = [{"title": "filtered"}]
    svc = _make_news_service()
    result = svc.get_news_data({"tickers": ["VCB"]})
    assert "VCB" in result["news"]
    assert result["news"]["VCB"][0]["title"] == "filtered"


def test_get_sentiment_data_no_tickers():
    svc = _make_news_service()
    result = svc.get_sentiment_data({"tickers": []})
    assert "note" in result


@patch.object(NewsSentimentService, "get_news_data")
def test_get_sentiment_data_basic(mock_news):
    mock_news.return_value = {
        "news": {"VCB": [{"title": "tăng mạnh", "content": "lợi nhuận khả quan"}]}
    }
    svc = _make_news_service()
    result = svc.get_sentiment_data({"tickers": ["VCB"]})
    assert "sentiment" in result
    assert "VCB" in result["sentiment"]


def test_analyze_news_sentiment_empty_tickers():
    svc = _make_news_service()
    result = svc.analyze_news_sentiment({"tickers": []})
    assert "error" in result


@patch("application.services.portfolio.news_sentiment_service._score_articles")
@patch.object(NewsSentimentService, "get_news_data")
def test_analyze_news_sentiment_combines(mock_news, mock_score):
    mock_news.return_value = {"news": {"VCB": [{"title": "a"}]}}
    mock_score.return_value = (0.5, {"label": "pos", "score": 0.5, "engine": "hf", "articles": []})
    svc = _make_news_service()
    result = svc.analyze_news_sentiment({"tickers": ["VCB"]})
    assert "VCB" in result
    assert result["VCB"]["sentiment"] == 0.5
    assert result["VCB"]["social_volume"] == 1
    assert result["VCB"]["sentiment_detail"]["label"] == "pos"


def test_compare_news_sentiment_no_tickers():
    svc = _make_news_service()
    result = svc.compare_news_sentiment({"tickers": []})
    assert "error" in result


@patch.object(NewsSentimentService, "get_sentiment_data")
def test_compare_news_sentiment_basic(mock_sent):
    mock_sent.return_value = {"sentiment": {"VCB": 0.5, "VNM": -0.2}}
    svc = _make_news_service()
    result = svc.compare_news_sentiment({"tickers": ["VCB"], "compare_with": ["VNM"]})
    assert result["VCB"] == 0.5
    assert result["VNM"] == -0.2


# -- handle_news_sentiment_query dispatch ---------------------------------


@patch.object(NewsSentimentService, "get_news_data")
def test_dispatch_news(mock_news):
    mock_news.return_value = {"news": {"VCB": []}}
    svc = _make_news_service()
    set_service("news", svc)
    from application.services.portfolio.news_sentiment_service import (
        handle_news_sentiment_query,
    )

    result = handle_news_sentiment_query(tickers=["VCB"], field="news")
    assert "news" in result


def test_dispatch_news_real_path():
    svc = _make_news_service(articles=[{"title": "VCB lãi lớn", "content": "lợi nhuận tăng"}])
    set_service("news", svc)
    from application.services.portfolio.news_sentiment_service import (
        handle_news_sentiment_query,
    )

    result = handle_news_sentiment_query(tickers=["VCB"], field="news")
    assert len(result["news"]["VCB"]) == 1


@patch.object(NewsSentimentService, "get_sentiment_data")
def test_dispatch_sentiment(mock_sent):
    mock_sent.return_value = {"sentiment": {"VCB": 0.0}}
    svc = _make_news_service()
    set_service("news", svc)
    from application.services.portfolio.news_sentiment_service import (
        handle_news_sentiment_query,
    )

    result = handle_news_sentiment_query(tickers=["VCB"], field="sentiment")
    assert "sentiment" in result


@patch("application.services.portfolio.news_sentiment_service._score_articles")
@patch.object(NewsSentimentService, "get_news_data")
def test_dispatch_fallback_to_analyze(mock_news, mock_score):
    mock_news.return_value = {"news": {"VCB": [{"title": "a"}]}}
    mock_score.return_value = (0.0, {"label": "neu", "score": 0.0, "engine": "hf", "articles": []})
    svc = _make_news_service()
    set_service("news", svc)
    from application.services.portfolio.news_sentiment_service import (
        handle_news_sentiment_query,
    )

    result = handle_news_sentiment_query(tickers=["VCB"], field="unknown")
    assert "VCB" in result


def test_dispatch_compare_sentiment_only():
    from application.services.portfolio.news_sentiment_service import (
        handle_news_sentiment_query,
    )

    result = handle_news_sentiment_query(tickers=["VCB"], compare_with=["VNM"], field="news")
    assert "error" in result


@patch.object(NewsSentimentService, "compare_news_sentiment")
def test_dispatch_compare_valid(mock_compare):
    mock_compare.return_value = {"VCB": 0.5, "VNM": -0.2}
    svc = _make_news_service()
    set_service("news", svc)
    from application.services.portfolio.news_sentiment_service import (
        handle_news_sentiment_query,
    )

    result = handle_news_sentiment_query(tickers=["VCB"], compare_with=["VNM"], field="all")
    assert "VCB" in result
