"""Exercise async-only MCP tools through the synchronous graph action node."""

import asyncio
from contextvars import ContextVar
import json

from langchain_core.tools import StructuredTool

from application.agents.custom_tool_node import CustomToolNode


def test_async_mcp_json_is_unwrapped_and_success_is_cached():
    invocations = []

    async def chart(amount: int):
        invocations.append(amount)
        return [{"type": "text", "text": json.dumps({"data": [{"value": amount}]})}]

    tool = StructuredTool.from_function(coroutine=chart, name="chart", description="Chart")
    node = CustomToolNode([tool])
    call = {"name": "chart", "args": {"amount": 6000000}, "id": "chart-1"}
    history, cache, retries = set(), {}, {}
    first = node.execute_one(call, history, cache, retries)
    assert json.loads(first) == {"data": [{"value": 6000000}]}
    assert node.execute_one(call, history, cache, retries) == first
    assert invocations == [6000000]


def test_async_mcp_inside_running_loop_preserves_context():
    request_context = ContextVar("test_request_context", default="missing")

    async def echo():
        return request_context.get()

    tool = StructuredTool.from_function(coroutine=echo, name="echo", description="Echo")
    node = CustomToolNode([tool])

    async def serving_request():
        token = request_context.set("request-123")
        try:
            return node._execute({"name": "echo", "args": {}})
        finally:
            request_context.reset(token)

    assert asyncio.run(serving_request()) == "request-123"


def test_sync_tool_is_still_invoked_once():
    def calculate(amount: int):
        return {"amount": amount}

    tool = StructuredTool.from_function(func=calculate, name="calculate", description="Calculate")
    assert json.loads(
        CustomToolNode([tool])._execute({"name": "calculate", "args": {"amount": 12}})
    ) == {"amount": 12}


def test_async_mcp_failure_is_visible_as_tool_error():
    async def unavailable():
        raise ConnectionError("MCP unavailable")

    tool = StructuredTool.from_function(
        coroutine=unavailable, name="unavailable", description="Unavailable"
    )
    assert (
        CustomToolNode([tool])._execute({"name": "unavailable", "args": {}})
        == "TOOL_ERR#UNKNOWN MCP unavailable"
    )
