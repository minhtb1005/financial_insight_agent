"""RED: FinancialRatioService serves snapshots from MarketStore (DB-first)."""

from application.services.financial.financial_ratio_service import (
    FinancialRatioService,
)
from infrastructure.market_store.store import MarketStore
from shared.ports.cache_port import CachePort
from shared.ports.financial_port import FinancialPort


class FakeCache(CachePort):
    def get(self, key):
        return None

    def set(self, key, value, ttl_hours=1.0):
        pass

    def delete(self, key):
        pass


class CountingPort(FinancialPort):
    def __init__(self):
        self.calls = 0

    def get_financial_statement(self, ticker):
        self.calls += 1
        raise AssertionError("live port must not be hit on DB hit")

    def get_market_data(self, ticker):
        self.calls += 1
        return {}


def test_db_hit_skips_live_port(tmp_path):
    store = MarketStore(tmp_path / "t.db")
    store.save_ratios("VCB", {"pe": 12.5}, period="2024", source="vnstock")
    try:
        svc = FinancialRatioService(cache=FakeCache(), financial_port=CountingPort(), store=store)
        out = svc.handle_query(tickers=["VCB"], field="pe")
        assert out["VCB"]["pe"]["value"] == 12.5
        assert out["VCB"]["data_as_of"]
        assert out["VCB"]["data_source"] == "vnstock"
    finally:
        store.close()


def test_db_miss_falls_back_to_live(tmp_path):
    import pandas as pd

    class LivePort(FinancialPort):
        def get_financial_statement(self, ticker):
            return pd.DataFrame(
                {
                    "item": ["P/E"],
                    "item_en": ["Price to Earning"],
                    "item_id": ["price_to_earning"],
                    "2024": [11.0],
                }
            )

        def get_market_data(self, ticker):
            return {}

    store = MarketStore(tmp_path / "t.db")
    try:
        svc = FinancialRatioService(cache=FakeCache(), financial_port=LivePort(), store=store)
        out = svc.handle_query(tickers=["VCB"], field="pe")
        assert out["VCB"]["pe"]["value"] == 11.0
        # write-back cached the snapshot
        assert store.get_ratios("VCB")["pe"] == 11.0
    finally:
        store.close()
