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
    # Batch 2 nullable (extra columns, backfill null)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    version: Optional[str] = None
    env: Optional[str] = None
    cost: Optional[float] = None
    scores: Optional[str] = None
    tags: Optional[str] = None


class TraceListResponse(BaseModel):
    enabled: bool = True
    count: int = 0
    total: int = 0
    traces: list[TraceSummary] = Field(default_factory=list)


class TraceDetailResponse(BaseModel):
    enabled: bool = True
    trace: dict[str, Any]


class FeedbackIn(BaseModel):
    score: int = Field(..., ge=1, le=5, description="Điểm chấm tay 1-5")
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
async def list_traces(  # noqa: PLR0917 - keep public signature
    limit: int = Query(50, ge=1, le=_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    status: Optional[Literal["ok", "error", "running"]] = None,
    min_duration_ms: Optional[float] = Query(None, ge=0),
    name_filter: Optional[str] = Query(None, max_length=100),
    trace_id_search: Optional[str] = Query(None, max_length=100),
    from_ts: Optional[float] = Query(None, ge=0),
    to_ts: Optional[float] = Query(None, ge=0),
    sort_by: Literal["started_at", "duration_ms", "num_spans", "total_tokens"] = Query(
        "started_at"
    ),
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
    description="Human score 1-5 cạnh RAGAS auto. author = admin username.",
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
            trace_id,
            body.score,
            body.comment,
            author=admin.email or admin.name or "admin",
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


class CommentIn(BaseModel):
    comment: str = Field(..., min_length=1, max_length=2000)
    span_id: Optional[str] = None


class MetaPatch(BaseModel):
    session_id: Optional[str] = Field(None, max_length=100)
    user_id: Optional[str] = Field(None, max_length=100)
    version: Optional[str] = Field(None, max_length=50)
    env: Optional[str] = Field(None, max_length=50)
    cost: Optional[float] = Field(None, ge=0)
    scores: Optional[str] = Field(None, max_length=2000)
    tags: Optional[str] = Field(None, max_length=1000)


@router.post("/{trace_id}/comments", summary="Thêm comment per node (admin)")
async def post_comment(
    trace_id: str, body: CommentIn, admin: User = Depends(get_current_admin_user)
):
    store, _tracer = _get_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Tracing is disabled")
    if store.get_trace(trace_id) is None:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    row = store.add_comment(
        trace_id,
        body.comment,
        author=admin.email or admin.name or "admin",
        span_id=body.span_id,
    )
    return row


@router.get("/{trace_id}/comments", summary="Danh sách comments (admin)")
async def get_comments(trace_id: str, _admin: User = Depends(get_current_admin_user)):
    store, _tracer = _get_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Tracing is disabled")
    return {"trace_id": trace_id, "comments": store.list_comments(trace_id)}


@router.patch("/{trace_id}/meta", summary="Cập nhật cột nullable Batch 2 (admin)")
async def patch_meta(
    trace_id: str, body: MetaPatch, _admin: User = Depends(get_current_admin_user)
):
    store, _tracer = _get_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Tracing is disabled")
    if store.get_trace(trace_id) is None:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    store.update_trace_meta(trace_id, {k: v for k, v in body.model_dump().items() if v is not None})
    return {"trace_id": trace_id, "updated": True}


@router.delete("/{trace_id}", summary="Xóa trace (admin, confirm ở UI)")
async def delete_trace(trace_id: str, _admin: User = Depends(get_current_admin_user)):
    store, _tracer = _get_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Tracing is disabled")
    if not store.delete_trace(trace_id):
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    return {"trace_id": trace_id, "deleted": True}
