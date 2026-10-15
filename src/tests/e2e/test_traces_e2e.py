"""E2E traces (TestClient, DB temp — không cần server, không playwright).

Flow admin thật qua router: list search/sort + detail tree + feedback POST/GET.
Smoke mắt (backend up + login admin@finsight.vn) chạy riêng theo checklist.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.observability.tracing import SpanKind, Tracer, TraceStore


@pytest.fixture()
def e2e(tmp_path, monkeypatch):
    store = TraceStore(tmp_path / "e2e_traces.db")
    tracer = Tracer(store=store, enabled=True)
    with tracer.start_span("agent.run", SpanKind.AGENT) as root:
        root.attributes["memory"] = "e2e"
        with tracer.start_span("tool.get_stock_price", SpanKind.TOOL):
            pass
        with tracer.start_span("llm_provider.chain", SpanKind.NODE):
            pass

    import interfaces.api.routes.traces as traces_module
    from infrastructure.auth.dependencies import get_current_admin_user
    from infrastructure.db.models.user import User

    monkeypatch.setattr(traces_module, "get_tracer", lambda: tracer)
    app = FastAPI()
    app.include_router(traces_module.router)
    app.dependency_overrides[get_current_admin_user] = lambda: User(
        email="admin@finsight.vn", hashed_password="x", name="t", role="admin"
    )
    return TestClient(app)


def test_e2e_list_search_sort_total(e2e):
    body = e2e.get("/traces").json()
    assert body["total"] == 1 and body["count"] == 1
    tid = body["traces"][0]["trace_id"]
    assert e2e.get("/traces", params={"trace_id_search": tid[:6]}).json()["total"] == 1
    assert e2e.get("/traces", params={"trace_id_search": "zzz-miss"}).json()["total"] == 0
    r = e2e.get("/traces", params={"sort_by": "duration_ms", "sort_dir": "asc"})
    assert r.status_code == 200 and r.json()["total"] == 1


def test_e2e_detail_tree_depth(e2e):
    tid = e2e.get("/traces").json()["traces"][0]["trace_id"]
    trace = e2e.get(f"/traces/{tid}").json()["trace"]
    assert len(trace["spans"]) == 3
    by_parent: dict = {}
    for s in trace["spans"]:
        by_parent.setdefault(s.get("parent_span_id"), []).append(s["name"])
    assert "agent.run" in by_parent[None]
    kids = by_parent.get(trace["spans"][0]["span_id"], [])
    assert set(kids) == {"tool.get_stock_price", "llm_provider.chain"}


def test_e2e_feedback_roundtrip(e2e):
    tid = e2e.get("/traces").json()["traces"][0]["trace_id"]
    assert e2e.get(f"/traces/{tid}/feedback").json()["feedback"] == []
    r = e2e.post(f"/traces/{tid}/feedback", json={"score": 4, "comment": "e2e ok"})
    assert r.status_code == 200 and r.json()["author"] == "admin@finsight.vn"
    items = e2e.get(f"/traces/{tid}/feedback").json()["feedback"]
    assert len(items) == 1 and items[0]["score"] == 4
