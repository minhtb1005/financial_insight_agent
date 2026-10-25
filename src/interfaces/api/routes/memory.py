"""Memory routes — per-user memory inspection and cleanup."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from infrastructure.auth.dependencies import get_current_user
from infrastructure.db.models.user import User
from infrastructure.memory.memory_manager import get_memory_manager
from application.learning.policy import LearningContext

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryResponse(BaseModel):
    user_id: str
    memory: dict[str, Any]


@router.get(
    "",
    response_model=MemoryResponse,
    summary="Lấy memory của user hiện tại",
)
async def get_my_memory(
    top_k: int = Query(10, ge=1, le=50),
    tiers: str | None = Query(None, description="Comma-separated tiers: episodic"),
    current_user: User = Depends(get_current_user),
):
    mgr = get_memory_manager()
    if mgr is None:
        return MemoryResponse(user_id=current_user.id, memory={})
    memory_tiers = [t.strip() for t in tiers.split(",") if t.strip()] if tiers else None
    data = mgr.search_memory(
        query="", top_k=top_k, memory_tiers=memory_tiers, user_id=current_user.id
    )
    return MemoryResponse(user_id=current_user.id, memory=data)


@router.delete(
    "",
    summary="Xóa memory của user hiện tại",
)
async def clear_my_memory(
    current_user: User = Depends(get_current_user),
    track: Literal["personal_finance", "market_literacy"] | None = None,
    lesson_id: str | None = None,
):
    mgr = get_memory_manager()
    if mgr is None:
        return {"cleared": False, "detail": "Memory not available"}
    user_id = current_user.id
    if track:
        from fastapi import HTTPException
        from pydantic import ValidationError

        try:
            user_id = LearningContext(track=track, lesson_id=lesson_id or None).memory_user(user_id)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail="Bài học không thuộc lộ trình.") from exc
    ok = mgr.clear_all(user_id=user_id)
    return {"cleared": ok, "user_id": current_user.id}


@router.get(
    "/stats",
    summary="Thống kê memory của user hiện tại",
)
async def memory_stats(
    current_user: User = Depends(get_current_user),
):
    mgr = get_memory_manager()
    if mgr is None:
        return {"error": "Memory not available"}
    return mgr.get_stats(user_id=current_user.id)
