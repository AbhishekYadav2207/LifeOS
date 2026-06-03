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
                total_xp=0,
                current_streak=0, 
                max_streak=0, 
                rank="Beginner",
                focus_points=0,
                health_points=0,
                discipline_points=0,
                mind_points=0,
                energy_score=100,
                recovery_tokens=1,
                prestige_level=0,
                lifetime_xp=0,
                consistency_7d=0.0,
                consistency_30d=0.0,
                consistency_90d=0.0
            )
        )
        
    return BaseResponse(
        success=True, 
        data=UserStatResponse(
            total_points=user_stat.total_xp,
            total_score=user_stat.total_xp,
            total_xp=user_stat.total_xp,
            current_streak=user_stat.current_streak,
            max_streak=user_stat.max_streak,
            rank=user_stat.rank,
            focus_points=user_stat.focus_points,
            health_points=user_stat.health_points,
            discipline_points=user_stat.discipline_points,
            mind_points=user_stat.mind_points,
            energy_score=user_stat.energy_score,
            recovery_tokens=user_stat.recovery_tokens,
            prestige_level=user_stat.prestige_level,
            lifetime_xp=user_stat.lifetime_xp,
            consistency_7d=user_stat.consistency_7d,
            consistency_30d=user_stat.consistency_30d,
            consistency_90d=user_stat.consistency_90d
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


from fastapi import HTTPException
from app.models.stat import CategoryProgression, UserMilestone, ProgressionEvent
from app.models.habit import HabitMastery

@router.post("/prestige", response_model=BaseResponse[Dict[str, Any]])
async def prestige(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Triggers a prestige reset if the user has reached the Transcendent rank.
    """
    # 1. Fetch user stats
    stat_q = select(UserStat).where(UserStat.user_id == current_user.id)
    user_stat = (await db.execute(stat_q)).scalars().first()
    if not user_stat:
        raise HTTPException(status_code=404, detail="Stats not found")

    # Calculate current rank score
    all_cats_q = select(CategoryProgression).where(CategoryProgression.user_id == current_user.id)
    all_cats = (await db.execute(all_cats_q)).scalars().all()
    cat_levels = [c.category_level for c in all_cats]
    cat_xps = [c.category_xp for c in all_cats]
    lowest_cat_xp = min(cat_xps) if cat_xps else 0
    highest_cat_xp = max(cat_xps) if cat_xps else 0

    all_mastery_q = select(HabitMastery).where(HabitMastery.user_id == current_user.id)
    all_mastery = (await db.execute(all_mastery_q)).scalars().all()
    mastery_levels = [m.mastery_level for m in all_mastery]

    rank_score = scoring_svc.calculate_rank_score(
        total_xp=user_stat.total_xp,
        consistency_90d=user_stat.consistency_90d,
        category_levels=cat_levels,
        mastery_levels=mastery_levels,
        lowest_cat_xp=lowest_cat_xp,
        highest_cat_xp=highest_cat_xp
    )

    # Eligible check: Rank must be Transcendent or rank_score >= 400000
    if user_stat.rank != "Transcendent" and rank_score < 400000:
        raise HTTPException(
            status_code=400,
            detail=f"Not eligible for Prestige. Current rank is '{user_stat.rank}' and Rank Score is {rank_score:.1f}. Must exceed Transcendent (rank score >= 400000)."
        )

    # 2. Reset rank elements
    user_stat.prestige_level += 1
    user_stat.total_xp = 0
    user_stat.rank = "Beginner"
    
    # Reset category splits
    user_stat.focus_points = 0
    user_stat.health_points = 0
    user_stat.discipline_points = 0
    user_stat.mind_points = 0

    # Reset CategoryProgression levels and XP
    for cat_prog in all_cats:
        cat_prog.category_xp = 0
        cat_prog.category_level = 1

    # 3. Log milestone and progression event
    milestone = UserMilestone(
        user_id=current_user.id,
        milestone_type="prestige_reached",
        value=user_stat.prestige_level
    )
    db.add(milestone)

    prog_evt = ProgressionEvent(
        user_id=current_user.id,
        event_type="prestige_triggered",
        payload={
            "prestige_level": user_stat.prestige_level,
            "previous_rank_score": rank_score
        }
    )
    db.add(prog_evt)

    await db.commit()
    
    return BaseResponse(
        success=True,
        data={
            "prestige_level": user_stat.prestige_level,
            "rank": user_stat.rank,
            "total_xp": user_stat.total_xp,
            "lifetime_xp": user_stat.lifetime_xp
        },
        message=f"Prestige level {user_stat.prestige_level} unlocked! Rank progress reset."
    )
