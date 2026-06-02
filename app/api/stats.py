from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, Any

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.stat import UserStat
from app.schemas.responses import BaseResponse
from app.schemas.stat import UserStatResponse
from app.services import scoring_svc, execution_svc

router = APIRouter(prefix="/stats", tags=["Statistics"])

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
            data=UserStatResponse(
                total_points=0, 
                total_score=0,
                current_streak=0, 
                max_streak=0, 
                rank="Beginner",
                focus_points=0,
                health_points=0,
                discipline_points=0,
                mind_points=0
            )
        )
        
    current_rank = scoring_svc.get_rank_from_score(user_stat.total_points)
    
    return BaseResponse(
        success=True, 
        data=UserStatResponse(
            total_points=user_stat.total_points,
            total_score=user_stat.total_points,
            current_streak=user_stat.current_streak,
            max_streak=user_stat.max_streak,
            rank=current_rank,
            focus_points=user_stat.focus_points,
            health_points=user_stat.health_points,
            discipline_points=user_stat.discipline_points,
            mind_points=user_stat.mind_points
        )
    )

@router.post("/process-day", response_model=BaseResponse[Dict[str, Any]])
async def process_day(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manual trigger to process the previous day's logs.
    Uses the user's timezone to determine "yesterday".
    """
    result = await execution_svc.manual_process_day(db, current_user)
    return BaseResponse(
        success=True,
        data=result,
        message="Daily processing completed"
    )
