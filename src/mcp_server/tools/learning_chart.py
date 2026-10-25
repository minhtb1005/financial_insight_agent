"""Charts from explicit educational assumptions; never fetch market data."""

import json
import math
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import Field

from application.services.education.calculators import budget_50_30_20, future_value
from domain.entities.chart_spec import ChartSpec
from mcp_server.instance import mcp
from mcp_server.tools.helpers import _categorize_error


@mcp.tool(
    name="generate_learning_chart",
    description=(
        "Vẽ ngân sách mẫu 50/30/20 hoặc giá trị danh nghĩa/sức mua theo kịch bản giả định. "
        "Không dùng cho giá cổ phiếu. Hỏi đủ số liệu trước khi gọi. Đơn vị VND; lãi/lạm phát %/năm."
    ),
)
def generate_learning_chart(
    scenario: Literal["budget", "purchasing_power"],
    amount: Annotated[
        float, Field(gt=0, le=1e15, description="Thu nhập ròng hoặc số tiền ban đầu, VND")
    ],
    years: Annotated[int, Field(ge=1, le=50)] = 5,
    annual_rate_pct: Annotated[float, Field(gt=-100, le=100)] = 6,
    inflation_pct: Annotated[float, Field(gt=-100, le=100)] = 4,
) -> str:
    try:
        if scenario not in {"budget", "purchasing_power"}:
            raise ValueError("Kịch bản không được hỗ trợ")
        if not all(math.isfinite(v) for v in (amount, annual_rate_pct, inflation_pct)):
            raise ValueError("Giá trị phải hữu hạn")
        if not 0 < amount <= 1e15 or not isinstance(years, int) or not 1 <= years <= 50:
            raise ValueError("Số tiền hoặc số năm ngoài giới hạn")
        if not -100 < annual_rate_pct <= 100 or not -100 < inflation_pct <= 100:
            raise ValueError("Tỷ lệ ngoài giới hạn")
        if scenario == "budget":
            values = budget_50_30_20(amount)
            values["savings_20"] = round(amount) - values["needs_50"] - values["wants_30"]
            rows = [
                {"category": label, "value": values[key]}
                for label, key in (
                    ("Thiết yếu", "needs_50"),
                    ("Mong muốn", "wants_30"),
                    ("Tiết kiệm", "savings_20"),
                )
            ]
            chart_type, x_field = "donut", "category"
            names = ["Ngân sách (VND)"]
            title = "Ngân sách mẫu 50/30/20 · VND"
            assumptions = "Tỷ lệ minh họa, cần điều chỉnh theo hoàn cảnh; không phải mức bắt buộc."
        else:
            rows = []
            names = ["Danh nghĩa", "Sức mua hiện tại"]
            for year in range(years + 1):
                values = future_value(amount, annual_rate_pct, year, inflation_pct)
                for name, key in zip(names, ("nominal", "real"), strict=True):
                    rows.append({"year": year, "symbol": name, "value": values[key]})
            chart_type, x_field = "line", "year"
            title = "Giá trị danh nghĩa và sức mua · VND · kịch bản giả định"
            assumptions = (
                f"Lãi kép {annual_rate_pct}%/năm, lạm phát {inflation_pct}%/năm cố định, "
                "không góp/rút thêm; chưa tính phí, thuế; không phải dự báo."
            )
        source = f"calculator:{scenario}:amount={amount}:years={years}:rate={annual_rate_pct}:inflation={inflation_pct}"
        spec = ChartSpec.model_validate(
            {
                "chart_type": chart_type,
                "title": title,
                "x_field": x_field,
                "y_field": "value",
                "series": [{"name": name, "type": chart_type} for name in names],
                "sort": {"field": x_field, "order": "ascending"},
                "data": rows,
                "annotations": [{"text": assumptions}],
                "data_source": source,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return json.dumps(
            {
                "spec": spec.model_dump(mode="json"),
                "data_source": source,
                "assumptions": assumptions,
            },
            ensure_ascii=False,
            allow_nan=False,
        )
    except (ValueError, TypeError, OverflowError) as exc:
        return _categorize_error(exc)
