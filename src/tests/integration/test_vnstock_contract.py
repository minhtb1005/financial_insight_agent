"""Live contract tests against the real vnstock API (Layer 2).

Purpose: catch API-shape drift that mocks cannot see (e.g. the VCI
``news_title`` column-mapping bug that shipped 50 blank articles while
mocked tests stayed green).

Opt-in only — NOT in default CI:
    $env:RUN_LIVE_CONTRACT='1'; python -m pytest src/tests/integration/test_vnstock_contract.py -q

Rate discipline: one autouse pacing fixture sleeps 4s between tests
(vnstock Guest: 20 req/min). Fixed historical dates keep assertions stable;
"today" data is only asserted for shape, never exact values.
"""

import os
import time

import pytest

RUN_LIVE = os.getenv("RUN_LIVE_CONTRACT") == "1"
SKIP_REASON = "RUN_LIVE_CONTRACT!=1 — live vnstock contract tests are opt-in"

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture(autouse=True)
def _pace_guest_rate_limit():
    time.sleep(4)


def _adapter():
    from infrastructure.adapters.vn_stock_adapter import VNStockAdapter

    return VNStockAdapter()


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_price_shape_and_known_value_vcb():
    out = _adapter().get_price_data("VCB", "2024-06-28", "2024-06-28")
    assert set(out) >= {"ticker", "data", "start_date", "end_date"}
    assert len(out["data"]) == 1
    row = out["data"][0]
    assert set(row) >= {"date", "open", "high", "low", "close", "volume"}
    assert row["close"] == 56.11


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_price_volume_hpg_fixed_date():
    out = _adapter().get_price_data("HPG", "2024-07-05", "2024-07-05")
    assert out["data"][0]["volume"] == 12379504


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_price_range_fpt_week():
    out = _adapter().get_price_data("FPT", "2024-07-01", "2024-07-05")
    assert [r["date"] for r in out["data"]] == [
        "2024-07-01",
        "2024-07-02",
        "2024-07-03",
        "2024-07-04",
        "2024-07-05",
    ]


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_price_shapes_vnm_bid():
    for ticker in ("VNM", "BID"):
        out = _adapter().get_price_data(ticker, "2024-06-28", "2024-06-28")
        assert out["data"], f"empty data for {ticker}"
        assert out["data"][0]["close"] is not None


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_company_news_columns_present():
    """Regression test for the blank-article mapping bug: VCI must expose
    news_title/public_date columns (adapter maps these, not title/date)."""
    from vnstock import Company

    df = Company(symbol="VCB", source="VCI").news()
    assert df is not None and not df.empty
    assert "news_title" in df.columns
    assert "public_date" in df.columns
    assert df["news_title"].astype(bool).any()


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_news_adapter_mapping_live():
    from infrastructure.adapters.news_adapter import NewsAdapter

    arts = NewsAdapter().fetch_news("VCB")
    assert arts, "no articles returned"
    assert arts[0]["title"].strip(), "blank title — column mapping regressed"


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_cached_adapter_readthrough_live(tmp_path):
    from infrastructure.adapters.vn_stock_adapter import VNStockAdapter
    from infrastructure.market_store.cached_adapter import CachedMarketDataAdapter
    from infrastructure.market_store.store import MarketStore

    adapter = CachedMarketDataAdapter(inner=VNStockAdapter(), store=MarketStore(tmp_path / "t.db"))
    first = adapter.get_price_data("VCB", "2024-06-28", "2024-06-28")
    assert first["data"][0]["close"] == 56.11
    assert first["source"] == "vnstock" and first["data_as_of"]
    second = adapter.get_price_data("VCB", "2024-06-28", "2024-06-28")
    assert second["source"] == "db"
    assert second["data"][0]["close"] == 56.11


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_caff_rss_feeds_reachable():
    import feedparser
    import requests

    from infrastructure.adapters.rss_news_adapter import SITE_FEEDS

    for _site, url in SITE_FEEDS:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        assert resp.status_code == 200, url
        assert len(feedparser.parse(resp.content).entries) > 0, url


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_indicator_history_depth_vcb():
    out = _adapter().get_price_data("VCB", "2024-05-01", "2024-06-28")
    closes = [r["close"] for r in out["data"] if r.get("close") is not None]
    assert len(closes) >= 20  # SMA20 needs 20+ points


@pytest.mark.skipif(not RUN_LIVE, reason=SKIP_REASON)
def test_ratio_upstream_status():
    """Documents the Finance.ratio() upstream status (VCI -> KBS).

    Skips (green) while broken so the suite stays green; remove the skip
    when upstream is fixed — ratios ingest depends on this endpoint.
    v3.5.1: VCI KeyError 'data', KBS 404 CSTC (both verified 2026-09-10);
    v4.0 moved VCI Finance to a new REST API.
    """
    from vnstock.api.financial import Finance

    last_error: Exception | None = None
    for source in ("VCI", "KBS"):
        try:
            data = Finance(source=source, symbol="VCB", show_log=False).ratio()
            if data is not None and not getattr(data, "empty", False):
                return
            last_error = ValueError(f"{source} returned empty frame")
        except Exception as e:  # noqa: BLE001
            last_error = e
    pytest.skip(f"upstream vnstock Finance.ratio broken: {str(last_error)[:120]}")
