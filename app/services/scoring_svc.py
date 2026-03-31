from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import date
from typing import Dict, Any

from app.models.user import User
from app.models.stat import UserStat, UserPlanStat
from app.models.log import DailyLog

def get_rank_from_score(score: int) -> str:
    """Calculates the 9-level Rank based on the user's total score."""
    if score < 50: return "Beginner"
    if score < 150: return "Starter"
    if score < 300: return "Rising"
    if score < 500: return "Consistent"
    if score < 800: return "Focused"
    if score < 1200: return "Disciplined"
    if score < 1800: return "Advanced"
    if score < 2500: return "Elite"
    return "Master"

async def process_day(db: AsyncSession, current_user: User, process_date: date) -> Dict[str, Any]:
    """
    Processes the logs for a specific day:
    1. Mark pending as missed.
    2. Calculate scores.
    3. Update streaks and total points.
    4. Generate summary.
    """
    query = select(DailyLog).where(
        DailyLog.user_id == current_user.id,
        DailyLog.date == process_date
    )
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if not logs:
        return {"message": "No active tasks for this day.", "score_change": 0}
        
    total_score_change = 0
    all_completed = True
    
    plan_id = logs[0].plan_id
    
    for log in logs:
        if log.status == "pending":
            log.status = "missed"
            log.points_awarded = - (log.snapshot_base_score // 2) # Penalty logic
            all_completed = False
            
        elif log.status == "done":
            if log.late_flag:
                log.points_awarded = log.snapshot_base_score // 2 # 50% score for late
            else:
                log.points_awarded = log.snapshot_base_score # Full score
                
        total_score_change += log.points_awarded
        
    # Update Stats
    stat_query = select(UserStat).where(UserStat.user_id == current_user.id)
    stat_result = await db.execute(stat_query)
    user_stat = stat_result.scalars().first()
    
    if user_stat:
        user_stat.total_points += total_score_change
        if all_completed and len(logs) > 0:
            user_stat.current_streak += 1
            if user_stat.current_streak > user_stat.max_streak:
                user_stat.max_streak = user_stat.current_streak
        else:
            user_stat.current_streak = 0
            
    # Include Plan Stats logic for V1
    plan_stat_query = select(UserPlanStat).where(
        UserPlanStat.user_id == current_user.id, 
        UserPlanStat.plan_id == plan_id
    )
    plan_stat_result = await db.execute(plan_stat_query)
    plan_stat = plan_stat_result.scalars().first()
    
    if not plan_stat and plan_id is not None:
        plan_stat = UserPlanStat(user_id=current_user.id, plan_id=plan_id)
        db.add(plan_stat)
    
    if plan_stat:
        plan_stat.total_points += total_score_change
        if all_completed and len(logs) > 0:
            plan_stat.current_streak += 1
            if plan_stat.current_streak > plan_stat.max_streak:
                plan_stat.max_streak = plan_stat.current_streak
        else:
            plan_stat.current_streak = 0

    await db.commit()
    
    new_rank = get_rank_from_score(user_stat.total_points) if user_stat else "Beginner"
    
    return {
        "score_change": total_score_change,
        "new_total": user_stat.total_points if user_stat else 0,
        "streak": user_stat.current_streak if user_stat else 0,
        "rank": new_rank,
        "insight": "Great job today!" if all_completed else "Don't give up, try again tomorrow!",
        "processed_date": process_date
    }
