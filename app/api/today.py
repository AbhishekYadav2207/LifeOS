from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.responses import BaseResponse
from app.schemas.execution import TodayResponse, LogCompletionRequest, LogResponse
from app.services import execution_svc

router = APIRouter(prefix="/today", tags=["Today"])


@router.get("/", response_model=BaseResponse[TodayResponse])
async def get_today(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch today's habits based on active plan.
    
    Returns:
    - tasks: list of today's habits with status and points
    - summary: live preview of progress (earned_points, completion_pct, etc.)
    - backfill: info about auto-processed missed days
    
    Flow:
    1. Resolve local date using user's timezone
    2. Auto-process any missed past days
    3. Initialize today's logs if needed
    4. Return tasks + live summary + backfill info
    """
    data = await execution_svc.get_today_data(db, current_user)
    return BaseResponse(success=True, data=data)


@router.post("/habit/complete", response_model=BaseResponse[LogResponse])
async def complete_habit(
    request: LogCompletionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a daily habit as completed."""
    log = await execution_svc.mark_habit_completed(db, request, current_user)
    return BaseResponse(
        success=True,
        data=LogResponse(
            id=log.id,
            habit_name=log.snapshot_habit_name,
            category=log.category.value if hasattr(log.category, 'value') else log.category,
            status=log.status,
            awarded_points=log.awarded_points,
            late_flag=log.late_flag
        ),
        message="Habit marked as completed!"
    )


@router.post("/process", response_model=BaseResponse[Dict[str, Any]])
async def process_day(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manual trigger to process the previous day's logs.
    Uses the user's timezone to determine "yesterday".
    
    This is a manual override / debugging tool only.
    The system auto-processes missed days when GET /today is called.
    """
    result = await execution_svc.manual_process_day(db, current_user)
    return BaseResponse(
        success=True,
        data=result,
        message="Daily processing completed"
    )
