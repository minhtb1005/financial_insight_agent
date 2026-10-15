"""Unit tests for the /traces REST endpoints (isolated FastAPI app)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.observability.tracing import SpanKind, Tracer, TraceStore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    store = TraceStore(tmp_path / "api_traces.db")
    tracer = Tracer(store=store, enabled=True)
    with tracer.start_span("agent.run", SpanKind.AGENT) as root:
        root.attributes["marker"] = "api_test"
        with tracer.start_span("reason", SpanKind.NODE):
            pass

    import interfaces.api.routes.traces as traces_module
    from infrastructure.auth.dependencies import get_current_admin_user
    from infrastructure.db.models.user import User

    monkeypatch.setattr(traces_module, "get_tracer", lambda: tracer)

    app = FastAPI()
    app.include_router(traces_module.router)
    # Router requires admin auth; tests run without credentials.
    app.dependency_overrides[get_current_admin_user] = lambda: User(
        email="admin@test.local", hashed_password="x", name="t", role="admin"
    )
    return TestClient(app), store


class TestTracesApi:
    def test_list_returns_trace_summary(self, client):
        http, _store = client
        resp = http.get("/traces")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert body["count"] == 1
        row = body["traces"][0]
        assert row["root_name"] == "agent.run"
        assert row["num_spans"] == 2
        assert row["status"] == "ok"

    def test_list_filters_by_status(self, client):
        http, _store = client
        resp = http.get("/traces", params={"status": "error"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_detail_contains_span_tree(self, client):
        http, _store = client
        listed = http.get("/traces").json()["traces"][0]
        detail = http.get(f"/traces/{listed['trace_id']}")
        assert detail.status_code == 200
        trace = detail.json()["trace"]
        names = {s["name"] for s in trace["spans"]}
        assert names == {"agent.run", "reason"}

    def test_detail_404_for_unknown(self, client):
        http, _store = client
        assert http.get("/traces/nope").status_code == 404

    def test_disabled_tracer_returns_503_on_detail(self, tmp_path, monkeypatch):
        from infrastructure.observability.tracing import Tracer as _T

        disabled = _T(store=None, enabled=False)
        import interfaces.api.routes.traces as traces_module

        monkeypatch.setattr(traces_module, "get_tracer", lambda: disabled)
        from infrastructure.auth.dependencies import get_current_admin_user
        from infrastructure.db.models.user import User

        app = FastAPI()
        app.include_router(router := traces_module.router)
        app.dependency_overrides[get_current_admin_user] = lambda: User(
            email="admin@test.local", hashed_password="x", name="t", role="admin"
        )

        http = TestClient(app)
        resp = http.get("/traces/some-id")
        assert resp.status_code == 503
        listing = http.get("/traces")
        assert listing.json()["enabled"] is False

    def test_limit_validation(self, client):
        http, _store = client
        resp = http.get("/traces", params={"limit": 999})
        assert resp.status_code == 422

    def test_list_includes_total_backward_compat(self, client):
        http, _store = client
        body = http.get("/traces").json()
        assert body["total"] == 1
        assert body["count"] == 1

    def test_search_by_trace_id(self, client):
        http, _store = client
        listed = http.get("/traces").json()["traces"][0]
        tid = listed["trace_id"]
        hit = http.get("/traces", params={"trace_id_search": tid[:8]}).json()
        assert hit["total"] == 1
        miss = http.get("/traces", params={"trace_id_search": "zzz-no-such-trace"}).json()
        assert miss["total"] == 0

    def test_search_escapes_like_wildcards(self, client):
        http, _store = client
        body = http.get("/traces", params={"trace_id_search": "%_"}).json()
        assert body["total"] == 0

    def test_date_filter_from_to(self, client):
        http, _store = client
        listed = http.get("/traces").json()["traces"][0]
        ts = listed["started_at"]
        assert ts is not None
        inside = http.get("/traces", params={"from_ts": ts - 10, "to_ts": ts + 10}).json()
        assert inside["total"] == 1
        outside = http.get("/traces", params={"from_ts": ts + 10000}).json()
        assert outside["total"] == 0

    def test_sort_params_and_whitelist_reject(self, client):
        http, _store = client
        ok = http.get("/traces", params={"sort_by": "num_spans", "sort_dir": "asc"})
        assert ok.status_code == 200
        bad = http.get("/traces", params={"sort_by": "trace_id"})
        assert bad.status_code == 422
        bad_dir = http.get("/traces", params={"sort_dir": "sideways"})
        assert bad_dir.status_code == 422
