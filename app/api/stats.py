from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from typing import Dict, Any

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.stat import UserStat
from app.schemas.responses import BaseResponse
from app.schemas.stat import UserStatResponse
from app.services import scoring_svc

router = APIRouter(prefix="/stats", tags=["Statistics & Processing"])

@router.get("/profile", response_model=BaseResponse[UserStatResponse])
async def get_profile(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the current aggregated stats for the user's profile."""
    query = select(UserStat).where(UserStat.user_id == current_user.id)
    result = await db.execute(query)
    user_stat = result.scalars().first()
    
    if not user_stat:
        # Default empty profile
        return BaseResponse(
            success=True,
            data=UserStatResponse(total_points=0, current_streak=0, max_streak=0, rank="Beginner", username=current_user.email.split("@")[0])
        )
        
    current_rank = scoring_svc.get_rank_from_score(user_stat.total_points)
    
    return BaseResponse(
        success=True, 
        data=UserStatResponse(
            total_points=user_stat.total_points,
            current_streak=user_stat.current_streak,
            max_streak=user_stat.max_streak,
            rank=current_rank,
            username=current_user.email.split("@")[0]
        )
    )

@router.post("/process-day", response_model=BaseResponse[Dict[str, Any]])
async def process_day(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Manual trigger to process today's logs for the authenticated user.
    Simulates the end of day evaluation.
    """
    local_today = datetime.now(timezone.utc).date()
    evaluation_result = await scoring_svc.process_day(db, current_user, local_today)
    
    return BaseResponse(
        success=True,
        data=evaluation_result,
        message="Daily processing completed"
    )
