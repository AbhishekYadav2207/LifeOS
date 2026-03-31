from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.responses import BaseResponse
from app.schemas.execution import TodaysHabitResponse, LogCompletionRequest, LogResponse
from app.services import execution_svc

router = APIRouter(prefix="/execution", tags=["Daily Execution"])

@router.get("/today", response_model=BaseResponse[List[TodaysHabitResponse]])
async def get_today(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch today's habits based on active plan."""
    logs = await execution_svc.get_today_logs(db, current_user)
    return BaseResponse(success=True, data=logs)

@router.post("/habit/complete", response_model=BaseResponse[LogResponse])
async def complete_habit(request: LogCompletionRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark a daily habit as completed."""
    log = await execution_svc.mark_habit_completed(db, request, current_user)
    return BaseResponse(
        success=True, 
        data=LogResponse(
            id=log.id, 
            habit_name=log.snapshot_habit_name, 
            status=log.status, 
            points_awarded=log.points_awarded, 
            late_flag=log.late_flag
        ),
        message="Habit marked as completed!"
    )
