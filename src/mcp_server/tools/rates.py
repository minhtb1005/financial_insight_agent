"""MCP rates tool — 1 hàm đọc lãi suất từ SQL store (Layer-2 pilot).

Chỉ giáo dục, không khuyến nghị sản phẩm tiền gửi/vay cụ thể theo chính sách sản phẩm.
Mọi output kèm nguồn + ngày hiệu lực/ngày crawl để đối chiếu văn bản/SBV.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from infrastructure.rates_store.cached_adapter import RatesCachedAdapter
from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service


@mcp.tool(
    name="get_rates",
    description=(
        "Tra cứu lãi suất từ kho SQL: policy (điều hành SBV, QĐ 1123 hiệu lực 19/06/2023), "
        "deposit (huy động niêm yết), lending (cho vay), avg (bình quân SBV), "
        "vnibor, banks. SQL-first kèm data_as_of + source + stale. Chỉ giáo dục."
    ),
)
def get_rates(
    group: Annotated[str, Field(description="policy|deposit|lending|avg|vnibor|banks")] = "policy",
    bank: Annotated[str | None, Field(description="Mã NH (deposit/lending), None = tất cả")] = None,
    start: Annotated[str, Field(description="Từ ngày YYYY-MM-DD (deposit/lending/vnibor)")] = "",
    end: Annotated[str, Field(description="Đến ngày YYYY-MM-DD")] = "",
    force_refresh: Annotated[bool, Field(description="Bỏ qua cache policy, ingest lại")] = False,
) -> str:
    def _impl() -> dict:
        return RatesCachedAdapter().get(group, bank, start, end, force_refresh)

    return call_service("get_rates", _impl)
