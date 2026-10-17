"""Unit tests for sector_service — SectorService (strict DI, FakePorts).

No network: company listing and market data are faked.
"""

import pandas as pd

from shared.ports.cache_port import CachePort
from shared.ports.company_port import CompanyPort
from shared.ports.market_data_port import MarketDataPort
from shared.utils.cache_keys import make_cache_key


class FakeCache(CachePort):
    def __init__(self, store=None):
        self._store = store or {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ttl_hours=1.0):
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)


class FakeCompanyPort(CompanyPort):
    def __init__(self, df):
        self._df = df

    def get_overview(self, index="VNINDEX"):
        return self._df

    def list_companies(self, *args, **kwargs):
        return []


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


def _overview(rows):
    return pd.DataFrame(rows)


def _prices(closes):
    return [
        {
            "date": f"2026-03-{1 + i:02d}",
            "open": c - 1.0,
            "high": c + 1.0,
            "low": c - 1.0,
            "close": c,
            "volume": 1000 + i * 100,
        }
        for i, c in enumerate(closes)
    ]


def _make_service(df=None, rows=None, cache=None):
    from application.services.market.sector_service import SectorService

    return SectorService(
        cache=cache if cache is not None else FakeCache(),
        company_port=FakeCompanyPort(df if df is not None else _overview([])),
        market_data=FakeMarketData(rows if rows is not None else []),
    )


# -- handle_query validation ----------------------------------------------


def test_sector_empty_returns_error():
    svc = _make_service()
    assert "error" in svc.handle_query(sector="")


def test_sector_valid():
    svc = _make_service(
        df=_overview(
            [
                {"ticker": "VCB", "sector": "banking"},
                {"ticker": "VNM", "sector": "banking"},
            ]
        ),
        rows=_prices([100.0, 102.0]),
    )
    result = svc.handle_query(sector="banking")
    assert "error" not in result
    assert "ranked_tickers" in result
    assert result["total_tickers"] == 2
    assert result["ranked_tickers"][0]["data_as_of"] == "2026-03-10T00:00:00+00:00"


# -- SectorService._get_tickers_in_sector ---------------------------------


def test_get_tickers_in_sector_matches():
    svc = _make_service(
        df=_overview(
            [
                {"ticker": "VCB", "sector": "banking"},
                {"ticker": "VNM", "sector": "banking"},
                {"ticker": "HPG", "sector": "steel"},
            ]
        )
    )
    result = svc._get_tickers_in_sector("banking")
    assert "VCB" in result
    assert "VNM" in result
    assert "HPG" not in result


def test_get_tickers_in_sector_no_match():
    svc = _make_service(df=_overview([{"ticker": "VCB", "sector": "banking"}]))
    assert svc._get_tickers_in_sector("real_estate") == []


def test_get_tickers_in_sector_missing_columns():
    svc = _make_service(df=_overview([{"ticker": "VCB"}]))
    assert svc._get_tickers_in_sector("banking") == []


# -- _get_performance -----------------------------------------------------


def test_get_performance_normal():
    svc = _make_service(rows=_prices([100.0, 105.0]))
    result = svc._get_performance("VCB", "2026-03-01", "2026-03-08")
    assert result is not None
    assert result["ticker"] == "VCB"
    assert result["performance_pct"] == 5.0
    assert result["data_as_of"] == "2026-03-10T00:00:00+00:00"


def test_get_performance_insufficient_data():
    svc = _make_service(rows=_prices([100.0]))
    assert svc._get_performance("VCB", "2026-03-01", "2026-03-08") is None


def test_get_performance_empty_data():
    svc = _make_service(rows=[])
    assert svc._get_performance("VCB", "2026-03-01", "2026-03-08") is None


# -- handle_query ---------------------------------------------------------


def test_handle_query_empty_sector():
    svc = _make_service()
    assert "error" in svc.handle_query(sector="")


def test_handle_query_cache_hit():
    key = make_cache_key("sector", "banking", "performance", "1w")
    svc = _make_service(cache=FakeCache({key: {"cached": "result"}}))
    assert svc.handle_query(sector="banking") == {"cached": "result"}
