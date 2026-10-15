"""Duplicate tool-call metrics for the ReAct agent benchmark.

The agent's :class:`CustomToolNode` dedups identical calls (cache hit = no span,
zero cost) and retries up to ``_MAX_RETRIES`` after ``TOOL_ERR#``.  What remains
visible in the trace — and what this module measures — are *executed* spans:

- ``retry_rate``: share of tool spans that repeat a call whose previous
  attempt(s) with the same key all errored.  Retries are expected behaviour,
  **not** waste.
- ``wasteful_duplicate_rate``: share of tool spans that repeat a call which
  had already succeeded earlier in the same trace — a signal of a useless
  ReAct loop (re-fetching known-good data instead of answering).

Definitions
-----------
- Key = ``tool_name`` + normalized args (JSON, sorted keys).  Mirrors
  ``CustomToolNode._fingerprint``.
- Spans are processed in ``started_at`` order (``get_trace`` already returns
  them ordered; we sort defensively).
- A span is an *error* span when its outputs contain ``TOOL_ERR#`` (the marker
  :class:`CustomToolNode` writes) or its ``error`` field is set.
- Classification per span, in order:
  - key never seen before → ``first`` (records its outcome);
  - key seen before, all previous same-key spans errored → ``retry``;
  - key seen before, at least one previous same-key span succeeded → ``waste``.
- Rates are ``count / total_tool_spans``.  A trace with zero tool spans yields
  ``None`` (excluded from means, same convention as other metrics).

All helpers are pure functions (no DB/LLM) so they are unit-testable.
"""

from __future__ import annotations

import json
from typing import Any

_TOOL_ERR_PREFIX = "TOOL_ERR#"


def normalize_args(args: Any) -> str:
    """Canonical string for tool args (mirrors CustomToolNode fingerprinting)."""
    if args is None:
        return "{}"
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (json.JSONDecodeError, TypeError):
            return args
    try:
        return json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(args)


def span_key(name: Any, args: Any) -> str:
    """Identity of a tool call: ``name|normalized_args``."""
    return f"{name or ''}|{normalize_args(args)}"


def span_is_error(span: dict[str, Any]) -> bool:
    """True when the span's outputs carry the ``TOOL_ERR#`` marker or error set."""
    if span.get("error"):
        return True
    outputs = span.get("outputs")
    if outputs is None:
        return False
    if not isinstance(outputs, str):
        try:
            outputs = json.dumps(outputs, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            outputs = str(outputs)
    return _TOOL_ERR_PREFIX in outputs


def iter_tool_spans(trace_detail: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Executed tool spans of a trace in execution order.

    Only spans carrying the ``invocation`` attribute (written by
    ``CustomToolNode._trace_span`` as ``first_call`` / ``retry_N``) are
    counted — one per real execution.  Spans without it are duplicate
    recordings of the same execution from an older instrumentation version
    (verified: in ``data/traces/traces.db`` every such span duplicates the
    key of an attributed span in the same trace, zero orphans) and would
    otherwise inflate duplicates 2x.  Traces predating the attribute have no
    attributed spans at all — those fall back to counting every tool span.
    """
    if not trace_detail:
        return []
    spans = [s for s in (trace_detail.get("spans") or []) if s.get("kind") == "tool"]
    attributed = [s for s in spans if _invocation(s) is not None]
    counted = attributed if attributed else spans
    return sorted(counted, key=lambda s: (s.get("started_at") is None, s.get("started_at")))


def _invocation(span: dict[str, Any]) -> Any:
    attrs = span.get("attributes") or {}
    if isinstance(attrs, str):
        try:
            attrs = json.loads(attrs)
        except (json.JSONDecodeError, TypeError):
            return None
    if isinstance(attrs, dict):
        return attrs.get("invocation")
    return None


def duplicate_rates(trace_detail: dict[str, Any] | None) -> dict[str, Any]:
    """Compute retry / wasteful-duplicate rates for one case trace.

    Returns ``retry_rate`` / ``wasteful_duplicate_rate`` (``None`` when the
    trace has no tool spans) plus raw counts for auditability.
    """
    spans = iter_tool_spans(trace_detail)
    total = len(spans)
    if total == 0:
        return {
            "retry_rate": None,
            "wasteful_duplicate_rate": None,
            "total_tool_calls": 0,
            "retry_calls": 0,
            "wasteful_calls": 0,
        }
    error_keys: set[str] = set()
    ok_keys: set[str] = set()
    retry_calls = 0
    wasteful_calls = 0
    for span in spans:
        key = span_key(span.get("name"), span.get("inputs"))
        if key in ok_keys:
            wasteful_calls += 1
        elif key in error_keys:
            retry_calls += 1
        if span_is_error(span):
            error_keys.add(key)
        else:
            ok_keys.add(key)
    return {
        "retry_rate": round(retry_calls / total, 4),
        "wasteful_duplicate_rate": round(wasteful_calls / total, 4),
        "total_tool_calls": total,
        "retry_calls": retry_calls,
        "wasteful_calls": wasteful_calls,
    }
