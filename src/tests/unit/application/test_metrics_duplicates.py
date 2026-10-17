"""Unit tests for duplicate tool-call metrics (pure functions, no DB/LLM)."""

import sys
from pathlib import Path

EVALS_DIR = Path(__file__).parents[4] / "evals"
sys.path.insert(0, str(EVALS_DIR))

from metrics_duplicates import (
    duplicate_rates,
    normalize_args,
    span_is_error,
    span_key,
)


def _span(  # noqa: PLR0917 - keep public signature
    name, args, outputs="", error=None, started_at=0.0, invocation="first_call"
):
    attrs = {} if invocation is None else {"invocation": invocation}
    return {
        "name": name,
        "kind": "tool",
        "inputs": args,
        "outputs": outputs,
        "error": error,
        "started_at": started_at,
        "attributes": attrs,
    }


def _trace(spans):
    return {"trace_id": "t", "spans": spans}


class TestNormalizeArgs:
    def test_key_order_insensitive(self):
        assert normalize_args({"b": 1, "a": 2}) == normalize_args({"a": 2, "b": 1})

    def test_none_is_empty_object(self):
        assert normalize_args(None) == "{}"

    def test_json_string_parsed(self):
        assert normalize_args('{"b": 1, "a": 2}') == normalize_args({"a": 2, "b": 1})

    def test_span_key_mirrors_fingerprint(self):
        assert span_key("get_stock_price", {"tickers": ["VCB"]}) == (
            'get_stock_price|{"tickers": ["VCB"]}'
        )


class TestSpanIsError:
    def test_tool_err_marker(self):
        assert span_is_error(_span("t", {}, "TOOL_ERR#UNKNOWN boom")) is True

    def test_error_field(self):
        assert span_is_error(_span("t", {}, "ok", error="ValueError: x")) is True

    def test_clean_output(self):
        assert span_is_error(_span("t", {}, '{"VCB": {}}')) is False

    def test_none_outputs(self):
        assert span_is_error(_span("t", {}, None)) is False


class TestDuplicateRates:
    def test_no_trace_returns_none(self):
        res = duplicate_rates(None)
        assert res["retry_rate"] is None and res["wasteful_duplicate_rate"] is None
        assert res["total_tool_calls"] == 0

    def test_no_tool_spans_returns_none(self):
        res = duplicate_rates({"spans": [{"kind": "llm", "name": "x"}]})
        assert res["retry_rate"] is None and res["wasteful_duplicate_rate"] is None

    def test_all_first_calls_zero_rates(self):
        trace = _trace(
            [
                _span("get_stock_price", {"tickers": ["VCB"]}, '{"ok": 1}', started_at=1.0),
                _span("rank_stocks", {"tickers": ["VCB"]}, '{"ok": 1}', started_at=2.0),
            ]
        )
        res = duplicate_rates(trace)
        assert res["retry_rate"] == 0.0
        assert res["wasteful_duplicate_rate"] == 0.0
        assert res["total_tool_calls"] == 2

    def test_retry_after_error_not_waste(self):
        trace = _trace(
            [
                _span("get_stock_price", {"a": 1}, "TOOL_ERR#TIMEOUT", started_at=1.0),
                _span("get_stock_price", {"a": 1}, "TOOL_ERR#TIMEOUT", started_at=2.0),
                _span("get_stock_price", {"a": 1}, '{"ok": 1}', started_at=3.0),
            ]
        )
        res = duplicate_rates(trace)
        assert res["retry_calls"] == 2
        assert res["wasteful_calls"] == 0
        assert res["retry_rate"] == round(2 / 3, 4)
        assert res["wasteful_duplicate_rate"] == 0.0

    def test_repeat_after_success_is_wasteful(self):
        trace = _trace(
            [
                _span("get_stock_price", {"a": 1}, '{"ok": 1}', started_at=1.0),
                _span("get_stock_price", {"a": 1}, '{"ok": 1}', started_at=2.0),
            ]
        )
        res = duplicate_rates(trace)
        assert res["retry_calls"] == 0
        assert res["wasteful_calls"] == 1
        assert res["wasteful_duplicate_rate"] == 0.5

    def test_retry_then_repeat_counts_as_waste(self):
        # err -> retry(err) -> retry(ok) -> repeat(ok) = 2 retries + 1 wasteful
        trace = _trace(
            [
                _span("t", {"a": 1}, "TOOL_ERR#x", started_at=1.0),
                _span("t", {"a": 1}, "TOOL_ERR#x", started_at=2.0),
                _span("t", {"a": 1}, '{"ok": 1}', started_at=3.0),
                _span("t", {"a": 1}, '{"ok": 1}', started_at=4.0),
            ]
        )
        res = duplicate_rates(trace)
        assert res["retry_calls"] == 2
        assert res["wasteful_calls"] == 1
        assert res["retry_rate"] == 0.5
        assert res["wasteful_duplicate_rate"] == 0.25

    def test_different_args_not_duplicates(self):
        trace = _trace(
            [
                _span("t", {"a": 1}, '{"ok": 1}', started_at=1.0),
                _span("t", {"a": 2}, '{"ok": 1}', started_at=2.0),
            ]
        )
        res = duplicate_rates(trace)
        assert res["wasteful_duplicate_rate"] == 0.0

    def test_unordered_spans_sorted_by_time(self):
        trace = _trace(
            [
                _span("t", {"a": 1}, '{"ok": 1}', started_at=2.0),
                _span("t", {"a": 1}, '{"ok": 1}', started_at=1.0),
            ]
        )
        res = duplicate_rates(trace)
        assert res["wasteful_calls"] == 1

    def test_double_recorded_spans_ignored(self):
        # Older instrumentation recorded the same execution twice: once with
        # the invocation attribute, once without. Only one execution happened.
        trace = _trace(
            [
                _span("t", {"a": 1}, '{"ok": 1}', started_at=1.0, invocation="first_call"),
                _span("t", {"a": 1}, '{"ok": 1}', started_at=1.1, invocation=None),
            ]
        )
        res = duplicate_rates(trace)
        assert res["total_tool_calls"] == 1
        assert res["wasteful_duplicate_rate"] == 0.0

    def test_legacy_trace_without_invocation_counts_all(self):
        trace = _trace(
            [
                _span("t", {"a": 1}, '{"ok": 1}', started_at=1.0, invocation=None),
                _span("t", {"a": 1}, '{"ok": 1}', started_at=2.0, invocation=None),
            ]
        )
        res = duplicate_rates(trace)
        assert res["total_tool_calls"] == 2
        assert res["wasteful_calls"] == 1
