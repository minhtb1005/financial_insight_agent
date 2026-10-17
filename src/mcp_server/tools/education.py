"""MCP education tools — thin @mcp.tool wrappers over pure calculators.

Educational only (no product advice, TT 135/2025). PIT output always carries
source + effective date + verify note from the calculator itself.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from application.services.education import calculators as edu
from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service

_EDU_SUFFIX = " Chỉ giáo dục, không khuyến nghị sản phẩm cụ thể."


@mcp.tool(
    name="calculate_loan_schedule",
    description=(
        "Tính lịch trả nợ (dư nợ giảm dần) + so sánh snowball vs avalanche. "
        "Dùng cho câu hỏi vay/trả nợ. Trả JSON {monthly_payment, schedule, snowball, avalanche}."
        + _EDU_SUFFIX
    ),
)
def calculate_loan_schedule(
    principal: Annotated[float, Field(description="Dư nợ gốc VND")],
    annual_rate_pct: Annotated[float, Field(description="Lãi suất năm %")] = 12.0,
    months: Annotated[int, Field(description="Kỳ hạn tháng", ge=1)] = 12,
    extra_debts: Annotated[
        list[dict] | None,
        Field(
            description="Các khoản nợ thêm [{name,balance,annual_rate_pct,min_payment}] để so sánh snowball/avalanche"
        ),
    ] = None,
    monthly_budget: Annotated[
        float | None, Field(description="Tổng ngân sách trả nợ/tháng (bắt buộc nếu có extra_debts)")
    ] = None,
) -> str:
    def _impl() -> dict:
        out = edu.amortize_loan(principal, annual_rate_pct, months)
        if extra_debts:
            if not monthly_budget:
                raise ValueError("monthly_budget required when extra_debts given")
            debts = [
                {
                    "name": "main",
                    "balance": principal,
                    "annual_rate_pct": annual_rate_pct,
                    "min_payment": out["monthly_payment"],
                }
            ] + list(extra_debts)
            out["comparison"] = edu.compare_repayment(debts, monthly_budget)
        return out

    return call_service("calculate_loan_schedule", _impl)


@mcp.tool(
    name="calculate_future_value",
    description=(
        "Tính lãi kép (giá trị danh nghĩa + giá trị thực sau lạm phát) và chi phí sống "
        "khi về hưu theo 3 kịch bản lạm phát. Trả JSON {nominal, real, retirement}." + _EDU_SUFFIX
    ),
)
def calculate_future_value(
    present_value: Annotated[float, Field(description="Số tiền hiện tại VND")] = 100_000_000,
    annual_rate_pct: Annotated[float, Field(description="Lãi suất năm %")] = 6.0,
    years: Annotated[float, Field(description="Số năm", ge=0)] = 5,
    inflation_pct: Annotated[float, Field(description="Lạm phát năm %")] = 4.0,
    monthly_cost_now: Annotated[
        float | None, Field(description="Chi phí sống/tháng hiện tại (để ước tính lúc hưu)")
    ] = None,
    years_to_retire: Annotated[float | None, Field(description="Số năm tới khi nghỉ hưu")] = None,
) -> str:
    def _impl() -> dict:
        out = edu.future_value(present_value, annual_rate_pct, years, inflation_pct)
        if monthly_cost_now is not None and years_to_retire is not None:
            out["retirement"] = edu.retirement_monthly(monthly_cost_now, years_to_retire)
        return out

    return call_service("calculate_future_value", _impl)


@mcp.tool(
    name="calculate_pit",
    description=(
        "Tính thuế TNCN từ tiền lương theo biểu hiện hành (Luật 109/2025, kỳ 2026). "
        "Kèm nguồn + ngày hiệu lực + câu đối chiếu trong output." + _EDU_SUFFIX
    ),
)
def calculate_pit(
    gross_monthly: Annotated[float, Field(description="Tổng thu nhập tháng VND")] = 30_000_000,
    dependents: Annotated[int, Field(description="Số người phụ thuộc", ge=0)] = 0,
    insurance: Annotated[float, Field(description="BHXH+BHYT+BHTN bắt buộc/tháng VND", ge=0)] = 0.0,
) -> str:
    return call_service(
        "calculate_pit",
        edu.calculate_pit,
        gross_monthly=gross_monthly,
        dependents=dependents,
        insurance=insurance,
    )


@mcp.tool(
    name="budget_template",
    description=(
        "Lập ngân sách 50/30/20 + zero-based từ thu nhập ròng. "
        "Gợi ý dùng generate_chart_spec (pie/donut) để vẽ cơ cấu." + _EDU_SUFFIX
    ),
)
def budget_template(
    net_income: Annotated[float, Field(description="Thu nhập ròng tháng VND", ge=0)] = 12_000_000,
    allocations: Annotated[
        dict[str, float] | None,
        Field(description="Phân bổ zero-based {hạng mục: VND}, None để chỉ dùng 50/30/20"),
    ] = None,
) -> str:
    def _impl() -> dict:
        out = {"plan_50_30_20": edu.budget_50_30_20(net_income)}
        if allocations is not None:
            out["zero_based"] = edu.zero_based(net_income, allocations)
        return out

    return call_service("budget_template", _impl)
