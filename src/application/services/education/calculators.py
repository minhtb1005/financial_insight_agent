"""Pure education calculators — no I/O, no network, fully testable offline.

Covers curriculum gaps M1 (budget), M3 (loan/snowball-avalanche), M4 (real rate),
M6 (PIT), M8 (future value / retirement). All money in VND, rates as percent.

Legal-number rule: every tax/rate constant carries its source + effective date
in the result so callers can cite it. PIT figures below verified against:
- Luật Thuế TNCN 2025 số 109/2025/QH15, Điều 9 (5-bracket schedule, applies to
  tax year 2026; law effective 01/07/2026)
- NQ 110/2025/UBTVQH15 + NĐ 253/2026/NĐ-CP (personal relief 15.5M/mo,
  dependent relief 6.2M/mo, applies to tax year 2026)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# PIT 2026 constants (cite + effective date — update here when law changes)
# ---------------------------------------------------------------------------
PIT_SOURCE = (
    "Luật Thuế TNCN 2025 số 109/2025/QH15 (Điều 9) + "
    "NQ 110/2025/UBTVQH15, NĐ 253/2026/NĐ-CP"
)
PIT_EFFECTIVE_DATE = "2026-01-01"  # kỳ tính thuế năm 2026 (Luật hiệu lực 01/07/2026)
# (upper bound of monthly taxable income in VND, rate)
PIT_BRACKETS_2026: tuple[tuple[float, float], ...] = (
    (10_000_000, 0.05),
    (30_000_000, 0.10),
    (60_000_000, 0.20),
    (100_000_000, 0.30),
    (float("inf"), 0.35),
)
PIT_PERSONAL_RELIEF = 15_500_000
PIT_DEPENDENT_RELIEF = 6_200_000
PIT_VERIFY_NOTE = (
    "Đối chiếu văn bản hiện hành trước khi quyết toán: "
    "Luật 109/2025/QH15 + NĐ 253/2026/NĐ-CP + TT 87/2026/TT-BTC."
)


def amortize_loan(principal: float, annual_rate_pct: float, months: int) -> dict:
    """Fixed-payment loan schedule (dư nợ giảm dần)."""
    if principal <= 0 or months <= 0:
        raise ValueError("principal and months must be positive")
    if annual_rate_pct < 0:
        raise ValueError("annual_rate_pct must be >= 0")
    r = annual_rate_pct / 100.0 / 12.0
    if r == 0:
        payment = principal / months
    else:
        payment = principal * r / (1.0 - (1.0 + r) ** (-months))
    schedule: list[dict] = []
    balance = principal
    total_interest = 0.0
    for m in range(1, months + 1):
        interest = balance * r
        principal_part = min(payment - interest, balance)
        balance -= principal_part
        total_interest += interest
        schedule.append({
            "month": m,
            "payment": round(payment, 0),
            "interest": round(interest, 0),
            "principal": round(principal_part, 0),
            "balance": round(max(balance, 0.0), 0),
        })
    return {
        "monthly_payment": round(payment, 0),
        "total_payment": round(payment * months, 0),
        "total_interest": round(total_interest, 0),
        "months": months,
        "schedule": schedule,
    }


def compare_repayment(debts: list[dict], monthly_budget: float) -> dict:
    """Snowball (trả dư nợ nhỏ nhất trước) vs avalanche (trả lãi cao nhất trước).

    Each debt: {"name": str, "balance": float, "annual_rate_pct": float,
    "min_payment": float}. monthly_budget must cover sum of minimums;
    the remainder attacks the target debt each month.
    """
    if not debts:
        raise ValueError("debts must be non-empty")
    if monthly_budget <= 0:
        raise ValueError("monthly_budget must be positive")
    mins = sum(d["min_payment"] for d in debts)
    if monthly_budget < mins:
        raise ValueError(f"monthly_budget {monthly_budget} below minimums total {mins}")

    def simulate(order: list[int]) -> dict:
        bals = [float(d["balance"]) for d in debts]
        rates = [d["annual_rate_pct"] / 100.0 / 12.0 for d in debts]
        mins_p = [float(d["min_payment"]) for d in debts]
        alive = [True] * len(debts)
        total_interest = 0.0
        total_paid = 0.0
        month = 0
        payoff_order: list[str] = []
        while any(alive):
            month += 1
            if month > 1200:  # ponytail: hard cap, upgrade to error if hit
                raise ValueError("repayment did not converge in 1200 months")
            interests = [b * r if a else 0.0 for b, r, a in zip(bals, rates, alive)]
            total_interest += sum(interests)
            remaining = monthly_budget
            # minimums first (interest + principal share)
            for i in range(len(debts)):
                if not alive[i]:
                    continue
                pay = min(mins_p[i], bals[i] + interests[i])
                to_interest = min(pay, interests[i])
                to_principal = pay - to_interest
                bals[i] -= to_principal
                remaining -= pay
                total_paid += pay
            # extra to target per strategy order
            for i in order:
                if remaining <= 0:
                    break
                if not alive[i] or bals[i] <= 0:
                    continue
                pay = min(remaining, bals[i])
                bals[i] -= pay
                remaining -= pay
                total_paid += pay
            for i in range(len(debts)):
                if alive[i] and bals[i] <= 0.01:
                    alive[i] = False
                    bals[i] = 0.0
                    payoff_order.append(debts[i]["name"])
        return {
            "payoff_order": payoff_order,
            "months": month,
            "total_interest": round(total_interest, 0),
            "total_paid": round(total_paid, 0),
        }

    snowball_order = sorted(range(len(debts)), key=lambda i: debts[i]["balance"])
    avalanche_order = sorted(range(len(debts)), key=lambda i: -debts[i]["annual_rate_pct"])
    snowball = simulate(snowball_order)
    avalanche = simulate(avalanche_order)
    return {
        "snowball": snowball,
        "avalanche": avalanche,
        "cheaper": "avalanche" if avalanche["total_interest"] <= snowball["total_interest"] else "snowball",
        "interest_saved": round(abs(snowball["total_interest"] - avalanche["total_interest"]), 0),
    }


def future_value(
    present_value: float,
    annual_rate_pct: float,
    years: float,
    inflation_pct: float = 0.0,
) -> dict:
    """Lãi kép danh nghĩa + giá trị thực sau lạm phát."""
    if present_value < 0 or years < 0:
        raise ValueError("present_value and years must be >= 0")
    nominal = present_value * (1.0 + annual_rate_pct / 100.0) ** years
    real = nominal / (1.0 + inflation_pct / 100.0) ** years if inflation_pct else nominal
    return {
        "nominal": round(nominal, 0),
        "real": round(real, 0),
        "years": years,
        "annual_rate_pct": annual_rate_pct,
        "inflation_pct": inflation_pct,
    }


def retirement_monthly(
    current_monthly_cost: float,
    years_to_retire: float,
    inflation_scenarios: tuple[float, ...] = (3.0, 5.0, 8.0),
) -> dict:
    """Chi phí sống/tháng khi về hưu theo từng kịch bản lạm phát (M8L2)."""
    if current_monthly_cost < 0 or years_to_retire < 0:
        raise ValueError("inputs must be >= 0")
    scenarios = [
        {
            "inflation_pct": inf,
            "future_monthly_cost": round(current_monthly_cost * (1.0 + inf / 100.0) ** years_to_retire, 0),
        }
        for inf in inflation_scenarios
    ]
    return {
        "current_monthly_cost": current_monthly_cost,
        "years_to_retire": years_to_retire,
        "scenarios": scenarios,
    }


def calculate_pit(
    gross_monthly: float,
    dependents: int = 0,
    insurance: float = 0.0,
) -> dict:
    """TNCN từ tiền lương theo biểu 2026 (xem hằng số + cite ở đầu file)."""
    if gross_monthly < 0 or dependents < 0 or insurance < 0:
        raise ValueError("inputs must be >= 0")
    taxable = gross_monthly - PIT_PERSONAL_RELIEF - PIT_DEPENDENT_RELIEF * dependents - insurance
    taxable = max(taxable, 0.0)
    breakdown: list[dict] = []
    remaining = taxable
    prev_cap = 0.0
    tax = 0.0
    for cap, rate in PIT_BRACKETS_2026:
        if remaining <= 0:
            break
        portion = min(remaining, cap - prev_cap)
        tax += portion * rate
        if portion > 0:
            breakdown.append({"bracket_up_to": None if cap == float("inf") else cap, "rate": rate, "portion": round(portion, 0), "tax": round(portion * rate, 0)})
        remaining -= portion
        prev_cap = cap
    return {
        "gross_monthly": gross_monthly,
        "dependents": dependents,
        "insurance": round(insurance, 0),
        "personal_relief": PIT_PERSONAL_RELIEF,
        "dependent_relief_each": PIT_DEPENDENT_RELIEF,
        "taxable_income": round(taxable, 0),
        "tax": round(tax, 0),
        "net_income": round(gross_monthly - insurance - tax, 0),
        "breakdown": breakdown,
        "source": PIT_SOURCE,
        "effective_date": PIT_EFFECTIVE_DATE,
        "verify_note": PIT_VERIFY_NOTE,
    }


def budget_50_30_20(net_income: float) -> dict:
    """Quy tắc 50/30/20 (M1L1)."""
    if net_income < 0:
        raise ValueError("net_income must be >= 0")
    return {
        "needs_50": round(net_income * 0.50, 0),
        "wants_30": round(net_income * 0.30, 0),
        "savings_20": round(net_income * 0.20, 0),
        "net_income": net_income,
        "method": "50/30/20",
    }


def zero_based(net_income: float, allocations: dict[str, float]) -> dict:
    """Zero-based: mọi đồng đều có nhiệm vụ; tổng phân bổ không vượt thu nhập."""
    if net_income < 0:
        raise ValueError("net_income must be >= 0")
    total = sum(allocations.values())
    if any(v < 0 for v in allocations.values()):
        raise ValueError("allocations must be >= 0")
    if total > net_income:
        raise ValueError(f"allocations total {total} exceeds income {net_income}")
    return {
        "net_income": net_income,
        "allocations": dict(allocations),
        "allocated": round(total, 0),
        "leftover": round(net_income - total, 0),
        "method": "zero-based",
    }
