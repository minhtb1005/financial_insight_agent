"""Unit tests for the market snapshot store (Phase 4a pilot).

Uses throwaway sqlite files (tmp_path) and a fake inner MarketDataPort —
no network, no vnstock.
"""

import pytest

from infrastructure.market_store.cached_adapter import CachedMarketDataAdapter
from infrastructure.market_store.store import MarketStore
from shared.base_service import BaseService


def _rows(start_day, n, close_start=10.0):
    from datetime import date, timedelta

    base = date.fromisoformat("2024-06-24")
    return [
        {
            "date": (base + timedelta(days=i)).isoformat(),
            "open": close_start + i,
            "high": close_start + i + 1,
            "low": close_start + i - 1,
            "close": close_start + i,
            "volume": 1000 + i,
        }
        for i in range(start_day, start_day + n)
    ]


class FakePort:
    """Counting fake inner port returning fixed rows."""

    def __init__(self, rows, error=None):
        self._rows = rows
        self._error = error
        self.calls = []

    def get_price_data(self, ticker, start_date, end_date, interval="1d"):
        self.calls.append((ticker, start_date, end_date, interval))
        if self._error:
            return {"error": self._error}
        return {
            "ticker": ticker,
            "data": self._rows,
            "start_date": start_date,
            "end_date": end_date,
        }


@pytest.fixture
def store(tmp_path):
    s = MarketStore(tmp_path / "test.db")
    yield s
    s.close()


class TestMarketStore:
    def test_upsert_and_get_roundtrip(self, store):
        assert store.upsert_prices("vcb", _rows(0, 3)) == 3
        rows = store.get_prices("VCB", "2024-06-24", "2024-06-26")
        assert [r["date"] for r in rows] == ["2024-06-24", "2024-06-25", "2024-06-26"]
        assert rows[0]["close"] == 10.0
        assert all(r["fetched_at"] for r in rows)

    def test_upsert_is_idempotent_replace(self, store):
        store.upsert_prices("VCB", _rows(0, 2))
        store.upsert_prices("VCB", _rows(0, 2, close_start=99.0))
        rows = store.get_prices("VCB", "2024-06-24", "2024-06-25")
        assert rows[0]["close"] == 99.0

    def test_coverage_and_meta(self, store):
        assert store.coverage("VCB")["rows"] == 0
        store.upsert_prices("VCB", _rows(0, 2))
        cov = store.coverage("VCB")
        assert (cov["min_date"], cov["max_date"], cov["rows"]) == ("2024-06-24", "2024-06-25", 2)
        assert cov["latest_fetch"]
        assert store.get_meta("k") is None
        store.set_meta("k", "v")
        assert store.get_meta("k") == "v"

    def test_ratios_roundtrip(self, store):
        assert store.save_ratios("VCB", {"pe": 15.5, "roe": 0.2}, period="Q2-2024") == 2
        got = store.get_ratios("VCB")
        assert got["pe"] == 15.5 and got["roe"] == 0.2
        assert got["_fetched_at"] and got["_source"] == "vnstock"


class TestCachedAdapter:
    def test_full_hit_no_inner_call(self, store):
        store.upsert_prices("VCB", _rows(0, 5))
        inner = FakePort([])
        out = CachedMarketDataAdapter(inner, store).get_price_data(
            "VCB", "2024-06-24", "2024-06-28"
        )
        assert inner.calls == []
        assert out["source"] == "db"
        assert len(out["data"]) == 5
        assert out["data_as_of"]

    def test_miss_fetches_and_caches(self, store):
        inner = FakePort(_rows(0, 2))
        out = CachedMarketDataAdapter(inner, store).get_price_data(
            "VCB", "2024-06-24", "2024-06-25"
        )
        assert len(inner.calls) == 1
        assert out["source"] == "vnstock"
        assert len(store.get_prices("VCB", "2024-06-24", "2024-06-25")) == 2

    def test_partial_hit_merges(self, store):
        store.upsert_prices("VCB", _rows(0, 2))
        inner = FakePort(_rows(0, 4))
        out = CachedMarketDataAdapter(inner, store).get_price_data(
            "VCB", "2024-06-24", "2024-06-27"
        )
        assert out["source"] == "mixed"
        assert [r["date"] for r in out["data"]] == [
            "2024-06-24",
            "2024-06-25",
            "2024-06-26",
            "2024-06-27",
        ]

    def test_inner_error_empty_store_returns_error(self, store):
        inner = FakePort([], error="boom")
        out = CachedMarketDataAdapter(inner, store).get_price_data(
            "VCB", "2024-06-24", "2024-06-25"
        )
        assert "error" in out

    def test_inner_error_partial_store_returns_partial(self, store):
        store.upsert_prices("VCB", _rows(0, 1))
        inner = FakePort([], error="boom")
        out = CachedMarketDataAdapter(inner, store).get_price_data(
            "VCB", "2024-06-24", "2024-06-25"
        )
        assert out["source"] == "db-partial"
        assert len(out["data"]) == 1

    def test_non_daily_delegates(self, store):
        inner = FakePort(_rows(0, 1))
        out = CachedMarketDataAdapter(inner, store).get_price_data(
            "VCB", "2024-06-24", "2024-06-24", interval="1h"
        )
        assert out["source"] == "vnstock"
        assert store.coverage("VCB")["rows"] == 0


class TestFreshnessHelper:
    def test_max_and_mixed(self):
        out = BaseService._freshness_of(
            {"data_as_of": "2024-01-01T00:00:00+00:00", "source": "db"},
            {"data_as_of": "2024-06-28T00:00:00+00:00", "source": "vnstock"},
        )
        assert out == {
            "data_as_of": "2024-06-28T00:00:00+00:00",
            "data_source": "mixed",
        }

    def test_single_source(self):
        out = BaseService._freshness_of({"data_as_of": "x", "source": "db"})
        assert out == {"data_as_of": "x", "data_source": "db"}

    def test_legacy_payloads_empty(self):
        assert BaseService._freshness_of({"ticker": "VCB"}, {"error": "x"}) == {}
        assert BaseService._freshness_of() == {}
