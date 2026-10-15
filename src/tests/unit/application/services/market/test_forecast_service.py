"""Unit tests for forecast_service — ForecastService (strict DI, FakePort).

No network: MarketDataPort is faked with fixed OHLCV rows; cache is faked.
"""

from unittest.mock import MagicMock

from shared.ports.cache_port import CachePort
from shared.ports.market_data_port import MarketDataPort
from shared.utils.cache_keys import make_cache_key


class FakeCache(CachePort):
    def __init__(self, store=None):
        self._store = store or {}

    def get(self, key): return self._store.get(key)
    def set(self, key, value, ttl_hours=1.0): self._store[key] = value
    def delete(self, key): self._store.pop(key, None)


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


def _rows(closes, start_day=1):
    return [
        {
            "date": f"2026-03-{start_day + i:02d}",
            "open": c - 1.0,
            "high": c + 1.0,
            "low": c - 2.0,
            "close": c,
            "volume": 1000,
        }
        for i, c in enumerate(closes)
    ]


def _make_service(rows, cache=None):
    from application.services.market.forecast_service import ForecastService

    return ForecastService(
        cache=cache if cache is not None else FakeCache(),
        market_data=FakeMarketData(rows),
    )


# -- handle_query ---------------------------------------------------------


def test_forecast_empty_tickers_returns_error():
    svc = _make_service(_rows([100.0] * 25))
    assert "error" in svc.handle_query(tickers=[])


def test_forecast_valid_ticker():
    svc = _make_service(_rows([float(i) for i in range(100, 120)]))
    result = svc.handle_query(tickers=["VCB"])
    assert "error" not in result, f"Unexpected error: {result}"
    assert "forecasts" in result
    assert result["model"] == "simple_moving_average"
    assert result["timeframe"] == "1w"
    fcast = result["forecasts"]["VCB"]
    assert fcast["ticker"] == "VCB"
    assert fcast["data_points"] >= 20
    assert fcast["last_price"] > 0
    assert fcast["projected_price"] > 0
    assert fcast["data_as_of"] == "2026-03-10T00:00:00+00:00"


def test_service_cache_hit():
    key = make_cache_key("forecast", "VCB", "1w")
    svc = _make_service(_rows([100.0] * 25), cache=FakeCache({key: {"cached": "forecast"}}))
    result = svc.handle_query(tickers=["VCB"])
    assert result == {
        "forecasts": {"VCB": {"cached": "forecast"}},
        "model": "simple_moving_average",
        "timeframe": "1w",
    }


# -- _forecast_single -----------------------------------------------------


def test_forecast_single_insufficient_data():
    svc = _make_service(_rows([100.0, 101.0]))
    result = svc._forecast_single("VCB", "1w")
    assert "error" in result
    assert "Insufficient" in result["error"]


def test_forecast_single_missing_close_column():
    svc = _make_service([{"date": "2026-03-01", "open": 100.0}] * 25)
    result = svc._forecast_single("VCB", "1w")
    assert "error" in result


def test_forecast_single_nan_values():
    closes = [float("nan")] * 25
    closes[0] = 100.0
    svc = _make_service(_rows(closes))
    result = svc._forecast_single("VCB", "1w")
    assert "error" in result


def test_forecast_all_tickers_fail_still_returns_error():
    svc = _make_service([])
    result = svc.handle_query(tickers=["VCB"])
    assert "forecasts" in result
    assert "error" in result["forecasts"]["VCB"]


def test_forecast_single_ticker_succeeds():
    svc = _make_service(_rows([float(i) for i in range(100, 125)]))
    result = svc.handle_query(tickers=["VCB"])
    assert "forecasts" in result
    fcast = result["forecasts"]["VCB"]
    assert fcast["ticker"] == "VCB"
    assert fcast["last_price"] > 0
    assert fcast["projected_price"] > 0
    assert "confidence_bounds" in fcast
    assert "lower" in fcast["confidence_bounds"]
    assert "upper" in fcast["confidence_bounds"]
    assert fcast["data_points"] >= 20


# -- edge cases -----------------------------------------------------------


def test_forecast_constant_close():
    svc = _make_service(_rows([100.0] * 25))
    result = svc.handle_query(tickers=["VCB"])
    assert "forecasts" in result
    assert result["forecasts"]["VCB"]["projected_price"] == 100.0


def test_forecast_negative_prices():
    svc = _make_service(_rows([float(-i) for i in range(100, 125)]))
    result = svc.handle_query(tickers=["VCB"])
    assert "forecasts" in result
    fcast = result["forecasts"]["VCB"]
    assert fcast["ticker"] == "VCB"
    assert fcast["projected_price"] < 0


def test_service_construction_uses_strict_di():
    svc = _make_service([])
    assert isinstance(svc._cache, FakeCache)
    assert isinstance(svc._market_data, FakeMarketData)
    assert isinstance(svc._market_data, MarketDataPort)
    assert not isinstance(svc._cache, MagicMock)
