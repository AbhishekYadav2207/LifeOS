from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import date
from typing import Dict, Any

from app.models.user import User
from app.models.stat import UserStat, UserPlanStat
from app.models.log import DailyLog, DailySummary
from app.models.enums import HabitCategory

def get_rank_from_score(score: int) -> str:
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
    # 1. Idempotency Check
    summary_q = select(DailySummary).where(
        DailySummary.user_id == current_user.id,
        DailySummary.date == process_date
    )
    is_processed = (await db.execute(summary_q)).scalars().first()
    if is_processed:
        return {"message": "Already processed", "score_change": 0, "status": "idempotent"}

    query = select(DailyLog).where(
        DailyLog.user_id == current_user.id,
        DailyLog.date == process_date
    )
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if not logs:
        return {"message": "No active tasks for this day.", "score_change": 0, "status": "no_op"}
        
    total_score_change = 0
    any_missed = False
    all_done = True
    plan_id = logs[0].plan_id
    
    # Category trackers
    cat_scores = {
        HabitCategory.focus: 0,
        HabitCategory.health: 0,
        HabitCategory.discipline: 0,
        HabitCategory.mind: 0
    }
    
    for log in logs:
        if log.status == "pending":
            log.status = "missed"
            log.awarded_points = - (log.snapshot_base_score // 2)
            any_missed = True
            all_done = False
        elif log.status == "done":
            if log.late_flag:
                log.awarded_points = log.snapshot_base_score // 2
            else:
                log.awarded_points = log.snapshot_base_score
            
        total_score_change += log.awarded_points
        cat_scores[log.category] += log.awarded_points
        
    # Update Stats
    stat_query = select(UserStat).where(UserStat.user_id == current_user.id)
    stat_result = await db.execute(stat_query)
    user_stat = stat_result.scalars().first()
    
    if user_stat:
        user_stat.total_points += total_score_change
        
        # Streak logic correction
        if any_missed:
            user_stat.current_streak = 0
        elif all_done and len(logs) > 0:
            user_stat.current_streak += 1
            if user_stat.current_streak > user_stat.max_streak:
                user_stat.max_streak = user_stat.current_streak

        user_stat.focus_points += cat_scores[HabitCategory.focus]
        user_stat.health_points += cat_scores[HabitCategory.health]
        user_stat.discipline_points += cat_scores[HabitCategory.discipline]
        user_stat.mind_points += cat_scores[HabitCategory.mind]
            
    # Plan Stats View
    plan_stat_query = select(UserPlanStat).where(
        UserPlanStat.user_id == current_user.id, 
        UserPlanStat.plan_id == plan_id
    )
    plan_stat_result = await db.execute(plan_stat_query)
    plan_stat = plan_stat_result.scalars().first()
    
    if not plan_stat and plan_id is not None:
        plan_stat = UserPlanStat(
            user_id=current_user.id, 
            plan_id=plan_id,
            total_points=0,
            current_streak=0,
            max_streak=0,
            focus_points=0,
            health_points=0,
            discipline_points=0,
            mind_points=0
        )
        db.add(plan_stat)
    
    if plan_stat:
        plan_stat.total_points += total_score_change
        if any_missed:
            plan_stat.current_streak = 0
        elif all_done and len(logs) > 0:
            plan_stat.current_streak += 1
            if plan_stat.current_streak > plan_stat.max_streak:
                plan_stat.max_streak = plan_stat.current_streak

        plan_stat.focus_points += cat_scores[HabitCategory.focus]
        plan_stat.health_points += cat_scores[HabitCategory.health]
        plan_stat.discipline_points += cat_scores[HabitCategory.discipline]
        plan_stat.mind_points += cat_scores[HabitCategory.mind]

    # Close the day stat out into idempotency state table
    db.add(DailySummary(
        user_id=current_user.id,
        date=process_date,
        total_score_change=total_score_change
    ))

    new_total = user_stat.total_points if user_stat else 0
    new_streak = user_stat.current_streak if user_stat else 0
    new_rank = get_rank_from_score(new_total)
    
    await db.commit()
    
    return {
        "score_change": total_score_change,
        "new_total": new_total,
        "streak": new_streak,
        "rank": new_rank,
        "insight": "Great job achieving your targets!" if all_done else "Don't break your momentum, lock in tomorrow!",
        "processed_date": process_date,
        "status": "processed"
    }
