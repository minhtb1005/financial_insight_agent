"""A failed provider chain must be visible as an error in local tracing."""

from unittest.mock import MagicMock

import pytest

import infrastructure.llm.llm_provider as llm_module
from infrastructure.llm.llm_provider import LLMChain
from infrastructure.observability.tracing import TraceStore, Tracer


def test_both_providers_fail_trace_is_error(monkeypatch, tmp_path):
    store = TraceStore(tmp_path / "provider-failure.db")
    tracer = Tracer(store=store, enabled=True)
    monkeypatch.setattr(llm_module, "get_tracer", lambda: tracer)
    primary = MagicMock()
    fallback = MagicMock()
    primary.invoke.side_effect = RuntimeError("primary unavailable")
    fallback.invoke.side_effect = RuntimeError("fallback unavailable")
    primary_cb = MagicMock()
    fallback_cb = MagicMock()
    primary_cb.acquire_permit.return_value = True
    fallback_cb.acquire_permit.return_value = True
    chain = LLMChain(primary, fallback, primary_cb, fallback_cb, "tool-calling")

    try:
        with pytest.raises(RuntimeError, match="fallback unavailable"):
            chain.invoke(["hello"])
        traces = store.list_traces(limit=10)
        assert len(traces) == 1
        assert traces[0]["status"] == "error"
    finally:
        store.close()
