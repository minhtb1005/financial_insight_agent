"""MCP tool: get_company_info."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from mcp_server.instance import mcp
from mcp_server.tools.helpers import call_service
from application.services.company.company_service import handle_company_query


@mcp.tool(
    name="get_company_info",
    description="Fetch company info: overview (business profile)|shareholders|executives|subsidiaries. Cite source and available date. Ask for ticker if absent.",
)
def get_company_info(
    tickers: Annotated[list[str], Field(description="Tickers")],
    field: Annotated[
        Literal["overview", "shareholders", "executives", "subsidiaries"],
        Field(description="overview for business profile; other fields for ownership/management"),
    ] = "shareholders",
) -> str:
    return call_service("get_company_info", handle_company_query, tickers=tickers, field=field)
