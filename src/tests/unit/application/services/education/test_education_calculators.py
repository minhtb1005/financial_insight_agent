"""Unit tests for education calculators — all numbers hand-computed (see comments)."""

import pytest

from application.services.education import calculators as edu


def test_amortize_standard():
    # 100M, 12%/yr, 12mo: P = 1M/(1-1.01^-12) = 8,884,878.87; interest 6,618,546
    out = edu.amortize_loan(100_000_000, 12.0, 12)
    assert abs(out["monthly_payment"] - 8_884_879) < 2
    assert abs(out["total_interest"] - 6_618_546) < 50
    assert len(out["schedule"]) == 12
    assert out["schedule"][-1]["balance"] == 0
    assert out["schedule"][0]["interest"] == pytest.approx(1_000_000, abs=1)


def test_amortize_zero_rate():
    out = edu.amortize_loan(120_000_000, 0.0, 12)
    assert out["monthly_payment"] == 10_000_000
    assert out["total_interest"] == 0


def test_amortize_invalid():
    with pytest.raises(ValueError):
        edu.amortize_loan(-1, 12.0, 12)
    with pytest.raises(ValueError):
        edu.amortize_loan(100, 12.0, 0)


_DEBTS = [
    {"name": "A", "balance": 10_000_000, "annual_rate_pct": 12.0, "min_payment": 1_000_000},
    {"name": "B", "balance": 5_000_000, "annual_rate_pct": 24.0, "min_payment": 1_000_000},
]


def test_compare_repayment_avalanche_cheaper():
    out = edu.compare_repayment(_DEBTS, 4_000_000)
    assert out["avalanche"]["payoff_order"][0] == "B"  # highest rate first
    assert out["snowball"]["payoff_order"][0] == "B"  # B is also smallest here
    assert out["avalanche"]["total_interest"] <= out["snowball"]["total_interest"]
    assert set(out["avalanche"]["payoff_order"]) == {"A", "B"}
    assert out["cheaper"] == "avalanche"


def test_compare_repayment_divergent_orders():
    debts = [
        {
            "name": "small-high",
            "balance": 3_000_000,
            "annual_rate_pct": 30.0,
            "min_payment": 500_000,
        },
        {"name": "big-low", "balance": 20_000_000, "annual_rate_pct": 8.0, "min_payment": 500_000},
    ]
    out = edu.compare_repayment(debts, 3_000_000)
    assert out["snowball"]["payoff_order"][0] == "small-high"
    assert out["avalanche"]["payoff_order"][0] == "small-high"  # highest rate too
    # make them diverge: small balance but LOW rate vs big HIGH rate
    debts2 = [
        {"name": "small-low", "balance": 3_000_000, "annual_rate_pct": 6.0, "min_payment": 500_000},
        {
            "name": "big-high",
            "balance": 20_000_000,
            "annual_rate_pct": 24.0,
            "min_payment": 500_000,
        },
    ]
    out2 = edu.compare_repayment(debts2, 3_000_000)
    assert out2["snowball"]["payoff_order"][0] == "small-low"
    # minimums clear the small debt first under both strategies, so the
    # avalanche advantage shows in interest, not payoff order
    assert out2["avalanche"]["total_interest"] <= out2["snowball"]["total_interest"]


def test_compare_repayment_budget_below_minimums():
    with pytest.raises(ValueError):
        edu.compare_repayment(_DEBTS, 1_000_000)


def test_future_value():
    # 100M * 1.08^5 = 146,932,808; real @4%: /1.04^5 = 120,768,058
    out = edu.future_value(100_000_000, 8.0, 5, 4.0)
    assert abs(out["nominal"] - 146_932_808) < 5
    assert abs(out["real"] - 120_768_058) < 50


def test_retirement_monthly():
    # 10M * 1.05^20 = 26,532,977
    out = edu.retirement_monthly(10_000_000, 20)
    by_inf = {s["inflation_pct"]: s["future_monthly_cost"] for s in out["scenarios"]}
    assert abs(by_inf[5.0] - 26_532_977) < 50
    assert by_inf[3.0] < by_inf[5.0] < by_inf[8.0]


def test_pit_zero_below_relief():
    out = edu.calculate_pit(15_000_000, dependents=0, insurance=0.0)
    assert out["taxable_income"] == 0
    assert out["tax"] == 0
    assert out["source"] and out["effective_date"] == "2026-01-01"
    assert "đối chiếu" in out["verify_note"].lower()


def test_pit_bracket_boundary():
    # gross 25.5M → taxable exactly 10M → 10M*5% = 500k
    out = edu.calculate_pit(25_500_000, dependents=0, insurance=0.0)
    assert out["taxable_income"] == 10_000_000
    assert out["tax"] == 500_000


def test_pit_two_brackets():
    # taxable 14.5M → 10M*5% + 4.5M*10% = 950k
    out = edu.calculate_pit(30_000_000, dependents=0, insurance=0.0)
    assert out["taxable_income"] == 14_500_000
    assert out["tax"] == 950_000
    assert len(out["breakdown"]) == 2


def test_pit_with_dependent_matches_published_case():
    # Reeracoen 2026 case: 30M salary, 1 dependent → ~257,500
    # (after ~3.15M compulsory insurance: taxable = 5.15M → 257,500)
    out = edu.calculate_pit(30_000_000, dependents=1, insurance=3_150_000)
    assert out["tax"] == 257_500


def test_pit_top_bracket():
    # taxable 100M → 0.5M + 2M + 6M + 12M = 20.5M
    out = edu.calculate_pit(115_500_000, dependents=0, insurance=0.0)
    assert out["tax"] == 20_500_000


def test_pit_net_and_invalid():
    out = edu.calculate_pit(20_000_000, dependents=0, insurance=2_100_000)
    assert out["tax"] == 120_000  # taxable 2.4M * 5%
    assert out["net_income"] == 20_000_000 - 2_100_000 - 120_000
    with pytest.raises(ValueError):
        edu.calculate_pit(-1)


def test_budget_50_30_20():
    out = edu.budget_50_30_20(12_000_000)
    assert (out["needs_50"], out["wants_30"], out["savings_20"]) == (
        6_000_000,
        3_600_000,
        2_400_000,
    )
    assert out["needs_50"] + out["wants_30"] + out["savings_20"] == 12_000_000


def test_zero_based():
    out = edu.zero_based(12_000_000, {"nha": 4_000_000, "an": 3_000_000, "tiet_kiem": 5_000_000})
    assert out["allocated"] == 12_000_000
    assert out["leftover"] == 0
    with pytest.raises(ValueError):
        edu.zero_based(10_000_000, {"a": 6_000_000, "b": 5_000_000})
