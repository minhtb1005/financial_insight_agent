"""Independent numerical fixtures for the teaching errors found in the live review."""

import json

import pytest

from application.services.education import calculators as edu
from mcp_server.tools.education import (
    budget_template,
    calculate_future_value,
    calculate_loan_schedule,
    calculate_pit,
)


def test_laptop_loan_total_matches_cash_paid_less_principal():
    out = edu.amortize_loan(12_000_000, 12, 6)
    assert out["monthly_payment"] == 2_070_580
    assert out["total_interest"] == 423_482
    assert out["total_payment"] - 12_000_000 == out["total_interest"]
    assert out["schedule"][-1]["balance"] == 0


def test_affordability_is_inverse_of_fixed_payment_schedule():
    out = edu.affordable_principal(9_000_000, 9, 240)
    assert abs(out["max_principal"] - 1_000_304_600) < 1000
    assert abs(edu.amortize_loan(out["max_principal"], 9, 240)["monthly_payment"] - 9_000_000) <= 1
    tool = json.loads(
        calculate_loan_schedule(payment_budget=9_000_000, annual_rate_pct=9, months=240)
    )
    assert tool["max_principal"] == out["max_principal"]


def test_zero_rate_affordability_and_ambiguous_inputs():
    assert edu.affordable_principal(1_000_000, 0, 12)["max_principal"] == 12_000_000
    assert "TOOL_ERR#" in calculate_loan_schedule(principal=10, payment_budget=10)


def test_risk_capital_cannot_consume_the_target_reserve():
    out = edu.reserve_capacity(100_000_000, 12_000_000, 6)
    assert out["reserve_target"] == 72_000_000
    assert out["uncommitted_surplus_before_other_obligations"] == 28_000_000
    assert edu.reserve_capacity(50_000_000, 12_000_000, 6)["reserve_shortfall"] == 22_000_000
    raw = budget_template(
        net_income=0, cash_available=100_000_000, essential_monthly=12_000_000, reserve_months=6
    )
    assert json.loads(raw)["reserve"] == out


def test_zero_income_cannot_fund_an_18m_replenishment():
    with pytest.raises(ValueError):
        edu.zero_based(15_000_000, {"reserve_replenishment": 18_000_000})


def test_tax_deducts_insurance_and_other_eligible_deductions():
    out = edu.calculate_pit(30_000_000, 1, 3_150_000, other_deductions=1_000_000)
    assert out["taxable_income"] == 4_150_000
    assert out["tax"] == 207_500
    assert out["net_income"] == 26_642_500
    assert "TOOL_ERR#" in calculate_pit(30_000_000, tax_year=2025)


def test_missing_income_is_not_silently_replaced_with_a_lesson_example():
    with pytest.raises(TypeError):
        calculate_pit()
    with pytest.raises(TypeError):
        budget_template()


def test_retirement_scenarios_include_the_requested_inflation_rate():
    out = json.loads(
        calculate_future_value(
            monthly_cost_now=15_000_000,
            years_to_retire=20,
            inflation_pct=4,
        )
    )
    scenarios = {
        row["inflation_pct"]: row["future_monthly_cost"] for row in out["retirement"]["scenarios"]
    }
    assert scenarios[4] == 32_866_847
    assert sorted(scenarios) == [2, 4, 6]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_invalid_financial_inputs_are_rejected(value):
    with pytest.raises(ValueError):
        edu.reserve_capacity(value, 1, 1)
    with pytest.raises(ValueError):
        edu.calculate_pit(value)
    with pytest.raises(ValueError):
        edu.affordable_principal(value, 5, 12)
