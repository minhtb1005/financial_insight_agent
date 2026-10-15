"""REST endpoints for browsing stored traces."""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from infrastructure.auth.dependencies import get_current_admin_user
from infrastructure.db.models.user import User
from infrastructure.observability.tracing import get_tracer

router = APIRouter(prefix="/traces", tags=["observability"])

_MAX_LIMIT = 200


class TraceSummary(BaseModel):
    trace_id: str = Field(..., description="Unique trace identifier")
    request_id: Optional[str] = None
    root_name: Optional[str] = None
    status: str = "running"
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    duration_ms: Optional[float] = None
    num_spans: int = 0
    total_tokens: int = 0
    llm_call_count: int = 0
    tool_call_count: int = 0


class TraceListResponse(BaseModel):
    enabled: bool = True
    count: int = 0
    total: int = 0
    traces: list[TraceSummary] = Field(default_factory=list)


class TraceDetailResponse(BaseModel):
    enabled: bool = True
    trace: dict[str, Any]


class FeedbackIn(BaseModel):
    score: int = Field(..., ge=1, le=5, description="Điểm chấm tay 1–5")
    comment: str = Field("", max_length=2000)
    span_id: Optional[str] = Field(None, description="Null = chấm cả trace")


class FeedbackOut(BaseModel):
    id: int
    trace_id: str
    span_id: Optional[str] = None
    score: int
    comment: str = ""
    author: str = ""
    created_at: str = ""


def _get_store():
    tracer = get_tracer()
    if not tracer.enabled or tracer.store is None:
        return None, tracer
    return tracer.store, tracer


@router.get(
    "",
    response_model=TraceListResponse,
    summary="Danh sách trace",
    description="Liệt kê các trace gần nhất với bộ lọc tùy chọn.",
)
async def list_traces(
    limit: int = Query(50, ge=1, le=_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    status: Optional[Literal["ok", "error", "running"]] = None,
    min_duration_ms: Optional[float] = Query(None, ge=0),
    name_filter: Optional[str] = Query(None, max_length=100),
    trace_id_search: Optional[str] = Query(None, max_length=100),
    from_ts: Optional[float] = Query(None, ge=0),
    to_ts: Optional[float] = Query(None, ge=0),
    sort_by: Literal["started_at", "duration_ms", "num_spans", "total_tokens"] = Query("started_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    _admin: User = Depends(get_current_admin_user),
):
    store, _tracer = _get_store()
    if store is None:
        return TraceListResponse(enabled=False, count=0, total=0, traces=[])
    try:
        rows = store.list_traces(
            limit=limit,
            offset=offset,
            status=status,
            min_duration_ms=min_duration_ms,
            name_filter=name_filter,
            trace_id_search=trace_id_search,
            from_ts=from_ts,
            to_ts=to_ts,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        total = store.count_traces(
            status=status,
            min_duration_ms=min_duration_ms,
            name_filter=name_filter,
            trace_id_search=trace_id_search,
            from_ts=from_ts,
            to_ts=to_ts,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Trace store read failed: {exc}") from exc
    return TraceListResponse(
        enabled=True,
        count=len(rows),
        total=total,
        traces=[TraceSummary(**row) for row in rows],
    )


@router.get(
    "/{trace_id}",
    response_model=TraceDetailResponse,
    summary="Chi tiết một trace",
    description="Trả về toàn bộ span tree của một trace theo trace_id.",
)
async def get_trace(trace_id: str, _admin: User = Depends(get_current_admin_user)):
    store, _tracer = _get_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Tracing is disabled")
    trace = store.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    return TraceDetailResponse(enabled=True, trace=trace)


@router.post(
    "/{trace_id}/feedback",
    response_model=FeedbackOut,
    summary="Chấm tay một trace (admin)",
    description="Human score 1–5 cạnh RAGAS auto. author = admin username.",
)
async def post_feedback(
    trace_id: str, body: FeedbackIn, admin: User = Depends(get_current_admin_user)
):
    store, _tracer = _get_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Tracing is disabled")
    if store.get_trace(trace_id) is None:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    try:
        row = store.add_feedback(
            trace_id, body.score, body.comment, author=admin.email or admin.name or "admin",
            span_id=body.span_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Feedback write failed: {exc}") from exc
    return FeedbackOut(**{k: row.get(k) for k in FeedbackOut.model_fields})


@router.get(
    "/{trace_id}/feedback",
    summary="Danh sách chấm tay của trace (admin)",
)
async def get_feedback(trace_id: str, _admin: User = Depends(get_current_admin_user)):
    store, _tracer = _get_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Tracing is disabled")
    return {"trace_id": trace_id, "feedback": store.list_feedback(trace_id)}
