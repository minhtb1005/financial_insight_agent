"""Unit: rates_store (retention/stale/hash/read-through) + pilot policy ingest."""

from infrastructure.rates_store.ingest import (
    POLICY_EFFECTIVE_DATE,
    ingest_policy_rates,
    parse_policy_rates,
)
from infrastructure.rates_store.store import RETENTION_MONTHS, RatesStore


def _mem_store() -> RatesStore:
    return RatesStore(db_path=":memory:")


SEED_LIKE = (
    "Lãi suất điều hành của Ngân hàng Nhà nước. "
    "Đang áp dụng: tái cấp vốn 4,5%/năm; tái chiết khấu 3,0%/năm; "
    "cho vay qua đêm/bù đắp thiếu hụt thanh toán 5,0%/năm — "
    "theo QĐ 1123/QĐ-NHNN, hiệu lực từ 19/06/2023."
)


def test_parse_policy_rates_hand_numbers():
    assert parse_policy_rates(SEED_LIKE) == {
        "tai_cap_von": 4.5,
        "tai_chiet_khau": 3.0,
        "qua_dem": 5.0,
    }


def test_retention_constants_per_table():
    assert RETENTION_MONTHS == {
        "deposit_listed": 12,
        "lending_listed": 12,
        "avg_rates_monthly": None,
        "policy_rates": None,
        "vnibor_daily": 6,
        "banks_meta": None,
    }


def test_policy_upsert_read_latest_with_source_dates():
    s = _mem_store()
    s.upsert_policy("tai_cap_von", 4.5, "2023-06-19", source="seed:test")
    s.upsert_policy("tai_cap_von", 4.0, "2022-01-01", source="seed:test")
    latest = s.latest_policy()
    assert latest["tai_cap_von"]["value"] == 4.5
    assert latest["tai_cap_von"]["effective_date"] == POLICY_EFFECTIVE_DATE
    assert latest["tai_cap_von"]["crawled_at"]  # UTC ISO set
    assert latest["tai_cap_von"]["source"] == "seed:test"
    s.close()


def test_ingest_hash_skip_second_run():
    s = _mem_store()
    r1 = ingest_policy_rates(s, text=SEED_LIKE, source="unit")
    assert r1["skipped"] is False
    assert r1["rates"]["tai_cap_von"] == 4.5
    r2 = ingest_policy_rates(s, text=SEED_LIKE, source="unit")
    assert r2["skipped"] is True
    assert len(s.get_policy()) == 3  # không ghi trùng
    s.close()


def test_ingest_fallback_unparseable_text():
    s = _mem_store()
    r = ingest_policy_rates(s, text="trang trống không có số", source="unit")
    assert r["source"] == "seed:sbv_policy_rates"
    assert r["rates"]["qua_dem"] == 5.0
    s.close()


def test_purge_deposit_keeps_recent_drops_old():
    s = _mem_store()
    s.upsert_deposit("VCB", "12M", 5.0, "2024-01-01", source="u")
    s.upsert_deposit("VCB", "12M", 5.3, "2025-10-01", source="u")
    n = s.purge_older_than("deposit_listed", "2025-01-01")
    assert n == 1
    rows = s.get_deposit("VCB")
    assert [r["date"] for r in rows] == ["2025-10-01"]
    s.close()


def test_purge_expired_vnibor_6mo_vs_policy_forever():
    s = _mem_store()
    s.upsert_vnibor("ON", 4.0, "2024-01-01", source="u")
    s.upsert_vnibor("ON", 4.4, "2025-10-01", source="u")
    s.upsert_policy("tai_cap_von", 4.5, "2023-06-19", source="u")
    out = s.purge_expired(today="2025-10-15")
    assert out["vnibor_daily"] == 1
    assert out["policy_rates"] == 0  # vĩnh viễn
    assert len(s.get_vnibor()) == 1
    assert len(s.get_policy()) == 1
    s.close()


def test_stale_empty_true_then_false_after_write():
    s = _mem_store()
    assert s.is_stale("policy_rates", 24) is True
    s.upsert_policy("tai_cap_von", 4.5, "2023-06-19", source="u")
    assert s.is_stale("policy_rates", 24) is False
    assert s.is_stale("policy_rates", 0) is True  # ngưỡng 0 → luôn stale
    s.close()


def test_avg_lending_bank_roundtrip():
    s = _mem_store()
    s.upsert_avg("cho_vay_bq", "2025-09", 9.1, source="sbv")
    s.upsert_lending("VCB", "sxkd", 7.5, "2025-10-01", source="web")
    s.upsert_bank("VCB", "Vietcombank", source="sbv")
    assert s.get_avg("cho_vay_bq")[0]["value"] == 9.1
    assert s.get_lending("VCB")[0]["rate"] == 7.5
    assert s.get_banks()[0]["bank_code"] == "VCB"
    s.close()


def test_adapter_policy_db_first_with_freshness():
    from infrastructure.rates_store.cached_adapter import RatesCachedAdapter

    s = _mem_store()
    s.upsert_policy("tai_cap_von", 4.5, "2023-06-19", source="u")
    out = RatesCachedAdapter(s).get("policy")
    assert out["data"][0]["value"] == 4.5
    assert out["data_as_of"]  # crawled_at mới nhất
    assert out["source"] == "db"
    assert out["stale"] is False  # vừa ghi → chưa stale 720h
    s.close()


def test_adapter_unknown_group_error():
    from infrastructure.rates_store.cached_adapter import RatesCachedAdapter

    out = RatesCachedAdapter(_mem_store()).get("nope")
    assert "error" in out and "policy" in out["valid_groups"]


def test_adapter_empty_deposit_stale_true():
    from infrastructure.rates_store.cached_adapter import RatesCachedAdapter

    out = RatesCachedAdapter(_mem_store()).get("deposit", bank="VCB")
    assert out["data"] == [] and out["stale"] is True
    assert out["data_as_of"] is None


def test_r1_minimums_all_groups_seed():
    from infrastructure.rates_store.ingest import ingest_all_r1

    s = _mem_store()
    out = ingest_all_r1(s)
    assert out["deposit"]["rows"] >= 12  # 4 NH x 4 ky (>=3x4)
    assert out["lending"]["rows"] >= 3
    assert out["avg"]["rows"] >= 1
    assert out["vnibor"]["rows"] >= 5
    assert out["banks"]["rows"] >= 5
    # acceptance hien thi: deposit du 4 NH x 4 ky
    deps = s.get_deposit()
    banks = {r["bank"] for r in deps}
    assert len(banks) >= 3 and all(
        len([r for r in deps if r["bank"] == b]) >= 4 for b in list(banks)[:3]
    )
    assert all(r["source"].startswith("seed:") for r in deps)
    # rerun -> skipped (hash)
    out2 = ingest_all_r1(s)
    assert all(v["skipped"] is True for v in out2.values())
    # get_rates verify tung nhom
    from infrastructure.rates_store.cached_adapter import RatesCachedAdapter

    a = RatesCachedAdapter(s)
    for g in ("deposit", "lending", "avg", "vnibor", "banks"):
        r = a.get(g)
        assert r["data"], g
        assert r["data_as_of"]
    s.close()
