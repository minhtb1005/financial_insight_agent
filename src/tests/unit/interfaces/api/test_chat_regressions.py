"""Regression coverage for the two chat queries reported on 2026-10-21."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

import application.agents.agent as agent_module
import interfaces.api.app as api_module
from application.agents.agent import StockAgent
from domain.entities.chart_spec import ChartSpec
from infrastructure.auth.dependencies import get_current_user
from infrastructure.guardrails.pipeline import GuardrailPipeline
from infrastructure.observability.tracing import TraceStore, Tracer


def _events(response):
    result = []
    for part in response.text.split("\n\n"):
        lines = part.splitlines()
        event = next((line[7:] for line in lines if line.startswith("event: ")), None)
        data = next((line[6:] for line in lines if line.startswith("data: ")), None)
        if event and data:
            result.append((event, data))
    return result


def _chart_spec():
    return ChartSpec(
        chart_type="line",
        title="VNM — 6 tháng",
        x_field="time",
        y_field="close",
        series=[{"name": "VNM", "type": "line"}],
        sort={"field": "time", "order": "ascending"},
        data=[{"time": "2026-10-01", "close": 60.0}],
        data_source="test-fixture",
    )


def _client(monkeypatch, tmp_path, graph_events):
    tracer = Tracer(store=TraceStore(tmp_path / "chat-traces.db"), enabled=True)
    agent = object.__new__(StockAgent)
    agent.reformulator = None
    agent.splitter = None
    agent.app = MagicMock()

    def completed_events(state, **_kwargs):
        for message, metadata in graph_events(state["original_query"]):
            if isinstance(message, AIMessage) and metadata.get("langgraph_node") == "final_answer":
                message.additional_kwargs["content_reviewed"] = True
            yield message, metadata

    agent.app.stream.side_effect = completed_events
    monkeypatch.setattr(agent_module, "get_tracer", lambda: tracer)
    monkeypatch.setattr(api_module, "get_tracer", lambda: tracer)
    monkeypatch.setattr(api_module, "agent", agent)
    monkeypatch.setattr(api_module, "_guardrail_pipeline", GuardrailPipeline())
    monkeypatch.setattr("infrastructure.memory.memory_manager.get_memory_manager", lambda: None)
    api_module.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="test-user")
    return TestClient(api_module.app), tracer.store


def test_bank_fees_query_reaches_agent_and_has_answer(monkeypatch, tmp_path):
    query = "Những khoản phí ngân hàng nào mình nên kiểm tra?"
    client, store = _client(
        monkeypatch,
        tmp_path,
        lambda _query: [
            (
                AIMessage(content="Kiểm tra phí duy trì và chuyển khoản."),
                {"langgraph_node": "final_answer"},
            )
        ],
    )
    try:
        response = client.post("/api/v1/ask-stream", json={"query": query})
        events = _events(response)
        assert response.status_code == 200
        assert any(kind == "chunk" and "phí duy trì" in json.loads(data) for kind, data in events)
        final = json.loads(next(data for kind, data in events if kind == "final"))
        assert final["answer"] == "Kiểm tra phí duy trì và chuyển khoản."
        traces = store.list_traces(limit=10)
        matching = [row for row in traces if row["request_id"] == final["request_id"]]
        assert len(matching) == 1
        assert matching[0]["status"] == "ok"
        trace = store.get_trace(matching[0]["trace_id"])
        stream_span = next(span for span in trace["spans"] if span["name"] == "http.stream")
        assert matching[0]["duration_ms"] >= stream_span["duration_ms"]
    finally:
        api_module.app.dependency_overrides.pop(get_current_user, None)
        store.close()


def test_explicit_unknown_symbol_returns_reason_and_error_trace(monkeypatch, tmp_path):
    client, store = _client(monkeypatch, tmp_path, lambda _query: [])
    try:
        response = client.post("/api/v1/ask-stream", json={"query": "Vẽ giá XXXX 6 tháng"})
        assert response.status_code == 400
        assert "XXXX" in response.json()["detail"]
        traces = store.list_traces(limit=10)
        failed = [row for row in traces if row["root_name"] == "http POST /api/v1/ask-stream"]
        assert len(failed) == 1
        assert failed[0]["status"] == "error"
    finally:
        api_module.app.dependency_overrides.pop(get_current_user, None)
        store.close()


def test_vnm_chart_tool_result_reaches_frontend(monkeypatch, tmp_path):
    chart = _chart_spec()

    def graph_events(_query):
        yield (
            ToolMessage(
                content=json.dumps({"spec": chart.model_dump(mode="json")}),
                tool_call_id="chart-1",
                name="generate_chart_spec",
            ),
            {"langgraph_node": "action"},
        )
        yield AIMessage(content="Đây là giá VNM."), {"langgraph_node": "final_answer"}

    client, store = _client(monkeypatch, tmp_path, graph_events)
    try:
        response = client.post(
            "/api/v1/ask-stream",
            json={
                "query": "Vẽ giá VNM 6 tháng",
                "learning_context": {"track": "market_literacy", "lesson_id": "MK2L1"},
            },
        )
        events = _events(response)
        chart_event = json.loads(next(data for kind, data in events if kind == "chart_spec"))
        assert json.loads(chart_event["spec"])["title"] == chart.title
        final = json.loads(next(data for kind, data in events if kind == "final"))
        assert "VNM — 6 tháng" in final["answer"]
        assert "1 phiên dữ liệu" in final["answer"]
        matching = [
            row for row in store.list_traces(limit=10) if row["request_id"] == final["request_id"]
        ]
        assert len(matching) == 1
        assert matching[0]["status"] == "ok"
    finally:
        api_module.app.dependency_overrides.pop(get_current_user, None)
        store.close()


def test_recovered_chart_retry_does_not_leave_error_in_chat(monkeypatch, tmp_path):
    chart = _chart_spec()

    def graph_events(_query):
        yield ToolMessage(
            content="TOOL_ERR#TIMEOUT", tool_call_id="chart-1", name="generate_chart_spec"
        ), {"langgraph_node": "action"}
        yield ToolMessage(
            content=json.dumps({"spec": chart.model_dump(mode="json")}),
            tool_call_id="chart-2",
            name="generate_chart_spec",
        ), {"langgraph_node": "action"}

    client, store = _client(monkeypatch, tmp_path, graph_events)
    try:
        response = client.post(
            "/api/v1/ask-stream",
            json={
                "query": "Vẽ giá VNM 6 tháng",
                "learning_context": {"track": "market_literacy", "lesson_id": "MK2L1"},
            },
        )
        events = _events(response)
        assert any(kind == "chart_spec" for kind, _ in events)
        assert not any(kind in ("chart_error", "error") for kind, _ in events)
        assert any(kind == "final" for kind, _ in events)
    finally:
        api_module.app.dependency_overrides.pop(get_current_user, None)
        store.close()


def test_llm_failure_is_error_event_and_error_trace(monkeypatch, tmp_path):
    client, store = _client(
        monkeypatch,
        tmp_path,
        lambda _query: [
            (
                AIMessage(
                    content="Trợ giảng AI chưa thể xử lý câu hỏi lúc này.",
                    additional_kwargs={"agent_error": "llm_unavailable"},
                ),
                {"langgraph_node": "reason"},
            )
        ],
    )
    try:
        response = client.post(
            "/api/v1/ask-stream",
            json={
                "query": "Vẽ giá VNM 6 tháng",
                "learning_context": {"track": "market_literacy", "lesson_id": "MK2L1"},
            },
        )
        events = _events(response)
        error = json.loads(next(data for kind, data in events if kind == "error"))
        assert error["error_type"] == "agent_error"
        assert "Trợ giảng AI" in error["detail"]
        assert not any(kind == "final" for kind, _ in events)
        matching = [
            row for row in store.list_traces(limit=10) if row["request_id"] == error["request_id"]
        ]
        assert len(matching) == 1
        assert matching[0]["status"] == "error"
    finally:
        api_module.app.dependency_overrides.pop(get_current_user, None)
        store.close()


def test_api_rejects_cross_track_lesson_before_graph(monkeypatch, tmp_path):
    client, store = _client(monkeypatch, tmp_path, lambda _query: [])
    try:
        response = client.post(
            "/api/v1/ask-stream",
            json={
                "query": "Vẽ giá VNM",
                "learning_context": {"track": "personal_finance", "lesson_id": "MK2L1"},
            },
        )
        assert response.status_code == 422
        api_module.agent.app.stream.assert_not_called()
    finally:
        api_module.app.dependency_overrides.pop(get_current_user, None)
        store.close()


def test_learning_chart_sse_and_scope_reach_graph(monkeypatch, tmp_path):
    from mcp_server.tools.learning_chart import generate_learning_chart

    payload = generate_learning_chart("budget", 12_000_000)

    def graph_events(_query):
        yield ToolMessage(content=payload, name="generate_learning_chart", tool_call_id="budget"), {
            "langgraph_node": "action"
        }
        yield AIMessage(content="Đây là ngân sách giả định, có thể điều chỉnh."), {
            "langgraph_node": "final_answer"
        }

    client, store = _client(monkeypatch, tmp_path, graph_events)
    try:
        response = client.post(
            "/api/v1/ask-stream",
            json={
                "query": "Vẽ ngân sách 12 triệu và giải thích",
                "learning_context": {"track": "personal_finance", "lesson_id": "M1L1"},
            },
        )
        assert response.status_code == 200
        state = api_module.agent.app.stream.call_args.args[0]
        assert state["learning_context"] == {"track": "personal_finance", "lesson_id": "M1L1"}
        assert any(kind == "chart_spec" for kind, _ in _events(response))
        assert (
            "giả định"
            in json.loads(next(data for kind, data in _events(response) if kind == "final"))[
                "answer"
            ]
        )
    finally:
        api_module.app.dependency_overrides.pop(get_current_user, None)
        store.close()
