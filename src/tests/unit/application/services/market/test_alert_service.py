"""Unit tests for alert_service — AlertService (strict DI, FakePort).

No network: MarketDataPort is faked with fixed OHLCV rows.
"""

from shared.ports.cache_port import CachePort
from shared.ports.market_data_port import MarketDataPort


class FakeCache(CachePort):
    def get(self, key): return None
    def set(self, key, value, ttl_hours=1.0): pass
    def delete(self, key): pass


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


def _rows(closes):
    return [
        {
            "date": f"2026-03-{8 + i:02d}",
            "open": c - 1.0,
            "high": c + 1.0,
            "low": c - 2.0,
            "close": c,
            "volume": 1000 + i * 100,
        }
        for i, c in enumerate(closes)
    ]


def _make_service(rows):
    from application.services.market.alert_service import AlertService

    return AlertService(cache=FakeCache(), market_data=FakeMarketData(rows))


# -- handle_query validation -------------------------------------------


def test_alert_empty_tickers_returns_error():
    svc = _make_service(_rows([105.0]))
    assert "error" in svc.handle_query(tickers=[], threshold=100.0)


def test_alert_none_threshold_returns_error():
    svc = _make_service(_rows([105.0]))
    assert "error" in svc.handle_query(tickers=["VCB"], threshold=None)


# -- threshold logic -----------------------------------------------------


def test_alert_above_threshold():
    svc = _make_service(_rows([100.0, 101.0, 105.0]))
    result = svc.handle_query(tickers=["VCB"], threshold=103.0, condition="above")
    alert = result["alerts"][0]
    assert alert["ticker"] == "VCB"
    assert alert["current_price"] == 105.0
    assert alert["threshold"] == 103.0
    assert alert["condition"] == "above"
    assert alert["triggered"] is True
    assert alert["data_as_of"] == "2026-03-10T00:00:00+00:00"


def test_alert_below_threshold_not_triggered():
    svc = _make_service(_rows([100.0, 101.0, 105.0]))
    result = svc.handle_query(tickers=["VCB"], threshold=103.0, condition="below")
    alert = result["alerts"][0]
    assert alert["ticker"] == "VCB"
    assert alert["current_price"] == 105.0
    assert alert["threshold"] == 103.0
    assert alert["condition"] == "below"
    assert alert["triggered"] is False


# -- AlertService._check_single ------------------------------------------


def test_check_single_no_data():
    svc = _make_service([])
    assert "error" in svc._check_single("VCB", 100.0, "above")


def test_check_single_missing_close():
    svc = _make_service([{"date": "2026-03-08", "open": 100.0},
                         {"date": "2026-03-09", "open": 101.0}])
    assert "error" in svc._check_single("VCB", 100.0, "above")


def test_check_single_price_equals_threshold():
    svc = _make_service(_rows([99.0, 100.0, 100.0]))
    result = svc._check_single("VCB", 100.0, "above")
    assert result["triggered"] is True
    assert result["current_price"] == 100.0
    assert result["threshold"] == 100.0
    assert result["condition"] == "above"


# -- handle_query summary -------------------------------------------------


def test_alert_summary():
    svc = _make_service(_rows([90.0, 95.0, 105.0]))
    result = svc.handle_query(tickers=["VCB", "HPG"], threshold=100.0, condition="above")
    assert "alerts" in result
    assert "summary" in result
    assert result["summary"]["total"] == 2
    assert result["summary"]["triggered"] == 2
    assert result["timeframe"] == "1d"


# -- edge cases -----------------------------------------------------------


def test_alert_zero_threshold():
    svc = _make_service(_rows([105.0]))
    result = svc.handle_query(tickers=["VCB"], threshold=0.0)
    assert "alerts" in result
    assert result["alerts"][0]["triggered"] is True


def test_alert_negative_threshold():
    svc = _make_service(_rows([105.0]))
    result = svc.handle_query(tickers=["VCB"], threshold=-50.0)
    assert "alerts" in result
    assert result["alerts"][0]["triggered"] is True


def test_alert_empty_data_closes():
    svc = _make_service([])
    result = svc.handle_query(tickers=["VCB"], threshold=100.0)
    assert "alerts" in result
    assert result["alerts"][0]["error"] == "No price data available"


def test_alert_single_point():
    svc = _make_service(_rows([105.0]))
    result = svc.handle_query(tickers=["VCB"], threshold=100.0, condition="above")
    assert "alerts" in result
    assert len(result["alerts"]) == 1
