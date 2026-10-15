"""Ingest ratios: chunked-resumable snapshot backfill (never raises per-ticker)."""

import pandas as pd

from infrastructure.market_store.ingest_ratios import backfill_ratios
from infrastructure.market_store.store import MarketStore


class FakePort:
    def __init__(self, fail=None):
        self.fail = set(fail or [])

    def get_financial_statement(self, ticker):
        if ticker in self.fail:
            raise RuntimeError("boom")
        return pd.DataFrame({
            "item": ["P/E", "ROE"],
            "item_en": ["Price to Earning", "Return on Equity"],
            "item_id": ["price_to_earning", "roe"],
            "2024": [10.0, 20.0],
        })

    def get_market_data(self, ticker):
        return {}


def test_backfill_writes_snapshots_and_resumes(tmp_path):
    store = MarketStore(tmp_path / "t.db")
    try:
        res = backfill_ratios(tickers=["VCB", "HPG"], port=FakePort(), store=store, sleep_s=0)
        assert res["done"] == ["VCB", "HPG"] and res["failed"] == {}
        assert store.get_ratios("VCB")["pe"] == 10.0
        res2 = backfill_ratios(tickers=["VCB", "HPG"], port=FakePort(), store=store, sleep_s=0)
        assert res2["skipped"] == ["VCB", "HPG"]
    finally:
        store.close()


def test_backfill_records_failure_and_continues(tmp_path):
    store = MarketStore(tmp_path / "t.db")
    try:
        res = backfill_ratios(tickers=["BAD", "VCB"], port=FakePort(fail={"BAD"}), store=store, sleep_s=0)
        assert "BAD" in res["failed"] and res["done"] == ["VCB"]
    finally:
        store.close()
