"""MCP education tools — thin @mcp.tool wrappers over pure calculators.

Educational only (no product advice under product policy). PIT output always carries
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
        "BẮT BUỘC dùng khi nêu số tiền vay/trả nợ, kể cả lãi 0%. "
        "Truyền principal để tính lịch trả tổng đều (annuity), hoặc payment_budget để tính "
        "ngược max_principal phù hợp khoản trả tháng; chỉ chọn một. Nêu lãi/kỳ/giả định phí."
        + _EDU_SUFFIX
    ),
)
def calculate_loan_schedule(  # noqa: PLR0917 - MCP exposes explicit calculator inputs
    principal: Annotated[
        float | None, Field(description="Dư nợ gốc VND, bỏ trống khi tính ngược")
    ] = None,
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
    payment_budget: Annotated[
        float | None,
        Field(
            description="Khoản trả/tháng VND để tính số tiền vay tối đa, không kèm principal", gt=0
        ),
    ] = None,
) -> str:
    def _impl() -> dict:
        if payment_budget is not None:
            if principal is not None or extra_debts or monthly_budget is not None:
                raise ValueError("payment_budget cannot be combined with principal/debt comparison")
            return edu.affordable_principal(payment_budget, annual_rate_pct, months)
        if principal is None:
            raise ValueError("Supply principal or payment_budget")
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
                },
                *list(extra_debts),
            ]
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
def calculate_future_value(  # noqa: PLR0917 - keep public signature
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
            out["retirement"] = edu.retirement_monthly(
                monthly_cost_now,
                years_to_retire,
                (max(0, inflation_pct - 2), inflation_pct, inflation_pct + 2),
            )
        return out

    return call_service("calculate_future_value", _impl)


@mcp.tool(
    name="calculate_pit",
    description=(
        "Tính thuế TNCN từ tiền lương theo biểu hiện hành (Luật 109/2025, kỳ 2026). "
        "Chỉ hỗ trợ cá nhân cư trú, tiền lương chịu thuế kỳ 2026; hỏi kỳ/cư trú và đầu vào thiếu. "
        "Giảm trừ 15,5/6,2 triệu, 5 bậc; KHÔNG dùng 11/4,4 triệu hay 7 bậc cho kỳ 2026. "
        "Thu nhập tính thuế trừ bảo hiểm và giảm trừ hợp lệ; không tự mặc định lương. "
        "Kèm nguồn + kỳ áp dụng; người phụ thuộc phải đủ điều kiện." + _EDU_SUFFIX
    ),
)
def calculate_pit(
    gross_monthly: Annotated[
        float, Field(description="Tiền lương thuộc diện chịu thuế tháng VND", ge=0)
    ],
    dependents: Annotated[int, Field(description="Số người phụ thuộc", ge=0)] = 0,
    insurance: Annotated[float, Field(description="BHXH+BHYT+BHTN bắt buộc/tháng VND", ge=0)] = 0.0,
    other_deductions: Annotated[
        float, Field(description="Giảm trừ hợp lệ khác đã kiểm điều kiện, không tính trùng", ge=0)
    ] = 0.0,
    tax_year: Annotated[int, Field(description="Kỳ tính thuế: chỉ hỗ trợ 2026")] = 2026,
) -> str:
    return call_service(
        "calculate_pit",
        edu.calculate_pit,
        gross_monthly=gross_monthly,
        dependents=dependents,
        insurance=insurance,
        other_deductions=other_deductions,
        tax_year=tax_year,
    )


@mcp.tool(
    name="budget_template",
    description=(
        "Lập ngân sách 50/30/20 + zero-based từ thu nhập ròng. "
        "Gợi ý dùng generate_learning_chart (budget) để vẽ cơ cấu. "
        "Có thể truyền cash_available, essential_monthly, reserve_months để kiểm quỹ và tiền dư "
        "trước chi/rủi ro; không chi vượt tiền thật có hoặc dùng vào quỹ phải giữ." + _EDU_SUFFIX
    ),
)
def budget_template(
    net_income: Annotated[
        float, Field(description="Thu nhập ròng tháng VND, không tự lấy từ ví dụ bài học", ge=0)
    ],
    allocations: Annotated[
        dict[str, float] | None,
        Field(description="Phân bổ zero-based {hạng mục: VND}, None để chỉ dùng 50/30/20"),
    ] = None,
    cash_available: Annotated[
        float | None, Field(description="Tiền thanh khoản thực có VND", ge=0)
    ] = None,
    essential_monthly: Annotated[
        float | None, Field(description="Chi thiết yếu/tháng VND", ge=0)
    ] = None,
    reserve_months: Annotated[
        float | None, Field(description="Số tháng quỹ mục tiêu, phải nêu giả định", ge=0)
    ] = None,
) -> str:
    def _impl() -> dict:
        out = {"plan_50_30_20": edu.budget_50_30_20(net_income)}
        if allocations is not None:
            out["zero_based"] = edu.zero_based(net_income, allocations)
        reserve_inputs = (cash_available, essential_monthly, reserve_months)
        if any(value is not None for value in reserve_inputs):
            if any(value is None for value in reserve_inputs):
                raise ValueError(
                    "cash_available, essential_monthly, reserve_months must be supplied together"
                )
            out["reserve"] = edu.reserve_capacity(*reserve_inputs)
        return out

    return call_service("budget_template", _impl)
