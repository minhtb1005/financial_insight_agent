import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from application.agents.agent import StockAgent
from application.learning.policy import CORE_TOOLS, MARKET_TOOLS, LearningContext
from interfaces.api.app import QueryRequest


def test_api_defaults_to_core_and_rejects_cross_track_or_client_tool_overrides():
    assert QueryRequest(query="phí ngân hàng").learning_context.track == "personal_finance"
    for context in (
        {"track": "full"},
        {"track": "personal_finance", "lesson_id": "MK2L1"},
        {"track": "market_literacy", "lesson_id": "M1L1"},
        {"track": "personal_finance", "tools": ["get_stock_price"]},
    ):
        with pytest.raises(ValidationError):
            QueryRequest(query="học", learning_context=context)


def test_action_blocks_injected_tool_even_if_result_is_cached():
    agent = object.__new__(StockAgent)
    agent.tool_node = MagicMock()
    result = agent._action_node(
        {
            "learning_context": {"track": "personal_finance"},
            "next_tool_call": [
                {"id": "1", "name": "get_stock_price", "args": {"tickers": ["VNM"]}}
            ],
            "tool_call_cache": {"get_stock_price": "cached secret"},
        }
    )
    agent.tool_node.execute_one.assert_not_called()
    assert json.loads(result["messages"][0].content)["error"] == "tool_not_allowed"


def test_lesson_scope_is_narrower_than_optional_track():
    assert "generate_chart_spec" in LearningContext(track="market_literacy").tools
    assert (
        "generate_chart_spec"
        not in LearningContext(track="market_literacy", lesson_id="MK1L1").tools
    )
    assert "get_stock_price" not in LearningContext().tools
    assert "predict_stock_price" not in LearningContext(track="market_literacy").tools


def test_concurrent_requests_bind_separate_tools_without_mutating_shared_registry():
    agent = object.__new__(StockAgent)
    agent.available_tools = [SimpleNamespace(name=name) for name in CORE_TOOLS | MARKET_TOOLS]
    agent.tools = agent.available_tools
    agent.llm = MagicMock()
    agent.llm_provider = SimpleNamespace(
        get_tool_calling_llm=lambda tools: SimpleNamespace(
            invoke=lambda messages, **kwargs: {t.name for t in tools}
        )
    )

    def invoke(track):
        return agent._invoke_llm(MagicMock(), [], track, {"track": track})[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        core, market = list(pool.map(invoke, ["personal_finance", "market_literacy"]))
    assert core == CORE_TOOLS
    assert market == MARKET_TOOLS
    assert len(agent.available_tools) == len(CORE_TOOLS | MARKET_TOOLS)


def test_dashboard_context_does_not_suppress_trusted_lesson_prompt():
    agent = object.__new__(StockAgent)
    state = {
        "messages": [HumanMessage(content="Giải thích")],
        "active_chart_spec": "a chart",
        "learning_context": {"track": "market_literacy", "lesson_id": "MK2L1"},
    }
    messages = agent._build_messages(state)
    assert isinstance(messages[0], SystemMessage)
    assert "MK2L1" in messages[0].content
    assert "không đưa lệnh mua/bán" in messages[0].content


def test_memory_scopes_do_not_mix_track_lesson_or_user():
    ids = {
        LearningContext(track=track, lesson_id=lesson).memory_user(user)
        for track, lesson in [
            ("personal_finance", None),
            ("personal_finance", "M1L1"),
            ("market_literacy", None),
        ]
        for user in ["a", "b"]
    }
    assert len(ids) == 6


def test_lesson_example_cannot_supply_ticker_for_conceptual_question():
    agent = object.__new__(StockAgent)
    agent.tool_node = MagicMock()
    result = agent._action_node(
        {
            "learning_context": {"track": "market_literacy", "lesson_id": "MK4L2"},
            "original_query": "P/E thấp có chắc tốt không?",
            "next_tool_call": [
                {"id": "1", "name": "get_financial_ratios", "args": {"tickers": ["VNM"]}}
            ],
        }
    )
    agent.tool_node.execute_one.assert_not_called()
    assert "TOOL_ERR#VALIDATION" in result["messages"][0].content


def test_explicit_or_active_chart_symbol_is_supported():
    from application.learning.policy import has_requested_symbols

    assert has_requested_symbols(
        "generate_chart_spec", {"symbols": ["VNM"]}, "vẽ vnm 6 tháng", None
    )
    assert has_requested_symbols("get_stock_price", {"tickers": ["VNM"]}, "mã này", "symbols VNM")
    assert not has_requested_symbols("get_stock_price", {"tickers": ["VNM", "FPT"]}, "VNM", None)


def test_scoped_binding_is_reused_and_provider_receives_request_timeout():
    agent = object.__new__(StockAgent)
    agent.llm = MagicMock()
    agent.available_tools = [SimpleNamespace(name=name) for name in CORE_TOOLS]
    agent.llm_provider = MagicMock()
    for _ in range(2):
        agent._invoke_llm(MagicMock(), [], "test", {"track": "personal_finance"})
    agent.llm_provider.get_tool_calling_llm.assert_called_once()
    bound = agent.llm_provider.get_tool_calling_llm.return_value
    assert bound.invoke.call_count == 2
    bound.invoke.assert_called_with([], timeout=45)
