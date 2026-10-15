"""Wiring tests: education MCP registration + tutor/full agent-mode filter."""

import json
from types import SimpleNamespace

import mcp_server.tools  # noqa: F401 — ensure registration
from mcp_server.instance import mcp


def test_mcp_has_18_tools_including_education():
    from mcp_server.tools import education  # noqa: F401

    assert len(mcp._tool_manager._tools) == 19
    for name in ("calculate_loan_schedule", "calculate_future_value", "calculate_pit", "budget_template"):
        assert name in mcp._tool_manager._tools


def test_pit_tool_output_carries_source_and_date():
    tool = mcp._tool_manager._tools["calculate_pit"]
    raw = tool.fn(gross_monthly=30_000_000, dependents=0, insurance=0.0)
    data = json.loads(raw)
    assert data["tax"] == 950_000
    assert "109/2025" in data["source"]
    assert data["effective_date"] == "2026-01-01"
    assert "đối chiếu" in data["verify_note"].lower()


def test_loan_tool_smoke():
    tool = mcp._tool_manager._tools["calculate_loan_schedule"]
    data = json.loads(tool.fn(principal=100_000_000, annual_rate_pct=12.0, months=12))
    assert abs(data["monthly_payment"] - 8_884_879) < 2


def test_budget_tool_smoke():
    tool = mcp._tool_manager._tools["budget_template"]
    data = json.loads(tool.fn(net_income=12_000_000))
    assert data["plan_50_30_20"]["needs_50"] == 6_000_000


def test_future_value_tool_smoke():
    tool = mcp._tool_manager._tools["calculate_future_value"]
    data = json.loads(tool.fn(present_value=100_000_000, annual_rate_pct=8.0, years=5, inflation_pct=4.0))
    assert abs(data["nominal"] - 146_932_808) < 5


def _fake_tools():
    return [SimpleNamespace(name=n) for n in (
        "get_stock_price", "calculate_loan_schedule", "calculate_future_value",
        "calculate_pit", "budget_template", "search_knowledge",
        "generate_chart_spec", "rank_stocks",
    )]


def test_agent_mode_full_keeps_all(monkeypatch):
    from application.agents.agent import _apply_agent_mode_filter

    monkeypatch.setenv("AGENT_MODE", "full")
    assert len(_apply_agent_mode_filter(_fake_tools())) == 8


def test_agent_mode_tutor_filters(monkeypatch):
    from application.agents.agent import _apply_agent_mode_filter

    monkeypatch.setenv("AGENT_MODE", "tutor")
    kept = {t.name for t in _apply_agent_mode_filter(_fake_tools())}
    assert kept == {
        "calculate_loan_schedule", "calculate_future_value", "calculate_pit",
        "budget_template", "search_knowledge", "generate_chart_spec",
    }
