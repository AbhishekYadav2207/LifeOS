from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from datetime import date, timedelta, datetime, time
from typing import Dict, Any
import uuid
import json

from app.models.user import User
from app.models.stat import UserStat, UserPlanStat, ScoreEvent, CategoryProgression, ProgressionEvent
from sqlalchemy.exc import IntegrityError
from app.models.log import DailyLog, DailySummary
from app.models.enums import HabitCategory
from app.models.scoring_version import ScoringVersion
from app.models.habit import HabitMastery
from app.models.plan import UserPlan, PlanHabit
from app.core.time import get_current_time

def get_rank_from_score(score: int) -> str:
    # Keep old function for v1 backward compatibility
    if score < 50: return "Beginner"
    if score < 150: return "Starter"
    if score < 300: return "Rising"
    if score < 500: return "Consistent"
    if score < 800: return "Focused"
    if score < 1200: return "Disciplined"
    if score < 1800: return "Advanced"
    if score < 2500: return "Elite"
    return "Master"

def calculate_rank_score(
    total_xp: int,
    consistency_90d: float,
    category_levels: list[int],
    mastery_levels: list[int],
    lowest_cat_xp: int,
    highest_cat_xp: int
) -> float:
    if highest_cat_xp == 0:
        balance_score = 1.0
    else:
        balance_score = (lowest_cat_xp + 1) / (highest_cat_xp + 1)
        
    category_score = round(sum(category_levels) * 100 * balance_score)
    mastery_score = sum(mastery_levels) * 50
    
    rank_score = (total_xp * 0.5) + (consistency_90d * 1000 * 0.2) + (category_score * 0.2) + (mastery_score * 0.1)
    return rank_score

def get_rank_from_rank_score(rank_score: float) -> str:
    if rank_score < 1000: return "Beginner"
    if rank_score < 3000: return "Starter"
    if rank_score < 6000: return "Rising"
    if rank_score < 10000: return "Consistent"
    if rank_score < 18000: return "Focused"
    if rank_score < 30000: return "Disciplined"
    if rank_score < 50000: return "Advanced"
    if rank_score < 80000: return "Elite"
    if rank_score < 120000: return "Master"
    if rank_score < 200000: return "Legend"
    if rank_score < 400000: return "Mythic"
    return "Transcendent"

def get_rank_level(rank: str) -> int:
    ranks = [
        "Beginner", "Starter", "Rising", "Consistent",
        "Focused", "Disciplined", "Advanced", "Elite",
        "Master", "Legend", "Mythic", "Transcendent"
    ]
    try:
        return ranks.index(rank) + 1
    except ValueError:
        return 1

def get_daily_xp_cap(rank_level: int) -> int:
    return 500 + (rank_level * 100)

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
    ).with_for_update()
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if not logs:
        return {"message": "No active tasks for this day.", "score_change": 0, "status": "no_op"}
        
    # Check scoring version from the day's logs
    day_scoring_version = logs[0].scoring_version if logs else "v2"

    if day_scoring_version == "v1":
        # Legacy daily processing logic
        total_score_change = 0
        any_missed = False
        all_done = True
        plan_id = logs[0].plan_id
        
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
                # Already populated during completion
                pass
                
            total_score_change += log.awarded_points
            cat_scores[log.category] += log.awarded_points
            
        # Update UserStat and lock the row
        stat_query = select(UserStat).where(UserStat.user_id == current_user.id).with_for_update()
        user_stat = (await db.execute(stat_query)).scalars().first()
        
        if user_stat:
            delta_val = max(0, user_stat.total_xp + total_score_change) - user_stat.total_xp
            user_stat.total_xp = max(0, user_stat.total_xp + total_score_change)
            if delta_val > 0:
                user_stat.lifetime_xp += delta_val
            
            if any_missed:
                user_stat.current_streak = 0
            elif all_done and len(logs) > 0:
                user_stat.current_streak += 1
                if user_stat.current_streak > user_stat.max_streak:
                    user_stat.max_streak = user_stat.current_streak

            user_stat.focus_points = max(0, user_stat.focus_points + cat_scores[HabitCategory.focus])
            user_stat.health_points = max(0, user_stat.health_points + cat_scores[HabitCategory.health])
            user_stat.discipline_points = max(0, user_stat.discipline_points + cat_scores[HabitCategory.discipline])
            user_stat.mind_points = max(0, user_stat.mind_points + cat_scores[HabitCategory.mind])
            
        # Plan Stats View
        if plan_id:
            plan_stat_query = select(UserPlanStat).where(
                UserPlanStat.user_id == current_user.id, 
                UserPlanStat.plan_id == plan_id
            )
            plan_stat = (await db.execute(plan_stat_query)).scalars().first()
            if not plan_stat:
                plan_stat = UserPlanStat(
                    user_id=current_user.id,
                    plan_id=plan_id,
                    total_xp=0,
                    current_streak=0,
                    max_streak=0,
                    focus_points=0,
                    health_points=0,
                    discipline_points=0,
                    mind_points=0
                )
                db.add(plan_stat)
            
            plan_stat.total_xp = max(0, plan_stat.total_xp + total_score_change)
            if any_missed:
                plan_stat.current_streak = 0
            elif all_done and len(logs) > 0:
                plan_stat.current_streak += 1
                if plan_stat.current_streak > plan_stat.max_streak:
                    plan_stat.max_streak = plan_stat.current_streak

                plan_stat.focus_points = max(0, plan_stat.focus_points + cat_scores[HabitCategory.focus])
                plan_stat.health_points = max(0, plan_stat.health_points + cat_scores[HabitCategory.health])
                plan_stat.discipline_points = max(0, plan_stat.discipline_points + cat_scores[HabitCategory.discipline])
                plan_stat.mind_points = max(0, plan_stat.mind_points + cat_scores[HabitCategory.mind])

        summary = DailySummary(
            user_id=current_user.id,
            date=process_date,
            total_score_change=total_score_change
        )
        db.add(summary)
        
        await db.commit()
        return {
            "score_change": total_score_change,
            "new_total": user_stat.total_xp if user_stat else 0,
            "streak": user_stat.current_streak if user_stat else 0,
            "rank": get_rank_from_score(user_stat.total_xp) if user_stat else "Beginner",
            "processed_date": process_date,
            "status": "processed"
        }

    # --- v2 Daily Processing Logic ---
    total_xp_change = 0
    completed_count = 0
    missed_count = 0
    plan_id = logs[0].plan_id
    
    for log in logs:
        if log.status == "pending":
            log.status = "missed"
            log.awarded_points = 0  # No negative XP under v2
            missed_count += 1
        elif log.status == "done":
            completed_count += 1
        elif log.status == "missed":
            missed_count += 1

    await db.flush()

    stat_query = select(UserStat).where(UserStat.user_id == current_user.id).with_for_update()
    user_stat = (await db.execute(stat_query)).scalars().first()
    
    if not user_stat:
        raise HTTPException(status_code=404, detail="Stats not found")

    # Apply Energy changes: -5 start decay, -10 per miss, +10 for perfect day
    energy_change = -5 - (10 * missed_count)
    perfect_day = (completed_count == len(logs)) and (len(logs) > 0)
    
    if perfect_day:
        energy_change += 10
        # Award Perfect Day XP Bonus
        perfect_xp = 50
        old_xp = user_stat.total_xp
        user_stat.total_xp += perfect_xp
        user_stat.lifetime_xp += perfect_xp
        total_xp_change += perfect_xp
        
        # Audit event for perfect day
        evt_id = str(uuid.uuid4())
        score_evt = ScoreEvent(
            event_id=evt_id,
            user_id=current_user.id,
            date=process_date,
            event_type="perfect_day_bonus",
            old_xp=old_xp,
            delta_xp=perfect_xp,
            new_xp=user_stat.total_xp,
            reason="Perfect Day Bonus XP"
        )
        db.add(score_evt)

    user_stat.energy_score = max(0, min(100, user_stat.energy_score + energy_change))

    # Streak Logic (streaks continue if no misses, or can be recovered later in Phase 2)
    if missed_count > 0:
        user_stat.current_streak = 0
    elif perfect_day:
        user_stat.current_streak += 1
        if user_stat.current_streak > user_stat.max_streak:
            user_stat.max_streak = user_stat.current_streak

    # Recalculate consistencies
    start_7d = process_date - timedelta(days=7)
    c7_q = select(DailyLog).where(
        DailyLog.user_id == current_user.id,
        DailyLog.date >= start_7d,
        DailyLog.date <= process_date,
        DailyLog.status.in_(["done", "missed"])
    )
    logs_7d = (await db.execute(c7_q)).scalars().all()
    c7_val = sum(1 for l in logs_7d if l.status == "done") / len(logs_7d) if logs_7d else 1.0

    start_30d = process_date - timedelta(days=30)
    c30_q = select(DailyLog).where(
        DailyLog.user_id == current_user.id,
        DailyLog.date >= start_30d,
        DailyLog.date <= process_date,
        DailyLog.status.in_(["done", "missed"])
    )
    logs_30d = (await db.execute(c30_q)).scalars().all()
    c30_val = sum(1 for l in logs_30d if l.status == "done") / len(logs_30d) if logs_30d else 1.0

    start_90d = process_date - timedelta(days=90)
    c90_q = select(DailyLog).where(
        DailyLog.user_id == current_user.id,
        DailyLog.date >= start_90d,
        DailyLog.date <= process_date,
        DailyLog.status.in_(["done", "missed"])
    )
    logs_90d = (await db.execute(c90_q)).scalars().all()
    c90_val = sum(1 for l in logs_90d if l.status == "done") / len(logs_90d) if logs_90d else 1.0

    user_stat.consistency_7d = c7_val
    user_stat.consistency_30d = c30_val
    user_stat.consistency_90d = c90_val

    # --- Recovery Tokens Generation Source ---
    # 1. 7 perfect days streak = +1 token
    if perfect_day and user_stat.current_streak > 0 and user_stat.current_streak % 7 == 0:
        if user_stat.recovery_tokens < 3:
            user_stat.recovery_tokens += 1
            prog_evt = ProgressionEvent(
                user_id=current_user.id,
                event_type="token_earned",
                payload={
                    "reason": "7_perfect_days_streak",
                    "current_streak": user_stat.current_streak,
                    "recovery_tokens": user_stat.recovery_tokens
                }
            )
            db.add(prog_evt)

    # 2. 30-day consistency > 95% = +1 token
    if user_stat.consistency_30d > 0.95:
        thirty_days_ago = process_date - timedelta(days=30)
        token_evt_q = select(ProgressionEvent).where(
            ProgressionEvent.user_id == current_user.id,
            ProgressionEvent.event_type == "token_earned",
            ProgressionEvent.created_at >= datetime.combine(thirty_days_ago, time.min)
        )
        recent_evts = (await db.execute(token_evt_q)).scalars().all()
        already_awarded = any(
            evt.payload.get("reason") == "consistency_30d" for evt in recent_evts
        )
        if not already_awarded:
            if user_stat.recovery_tokens < 3:
                user_stat.recovery_tokens += 1
                prog_evt = ProgressionEvent(
                    user_id=current_user.id,
                    event_type="token_earned",
                    payload={
                        "reason": "consistency_30d",
                        "consistency_30d": user_stat.consistency_30d,
                        "recovery_tokens": user_stat.recovery_tokens
                    }
                )
                db.add(prog_evt)

    # --- Burnout Detection ---
    active_plan = await db.execute(
        select(UserPlan).where(UserPlan.user_id == current_user.id, UserPlan.active == True)
    )
    active_plan_row = active_plan.scalars().first()
    if active_plan_row:
        ph_q = select(func.count(PlanHabit.id)).where(PlanHabit.plan_id == active_plan_row.plan_id)
        active_habits_count = (await db.execute(ph_q)).scalar() or 0
        if active_habits_count > 15:
            if c7_val < 0.40:
                # Log event
                burnout_evt = ProgressionEvent(
                    user_id=current_user.id,
                    event_type="burnout_detected",
                    payload={
                        "active_habits_count": active_habits_count,
                        "completion_rate_7d": c7_val,
                        "suggestion": "We detected potential burnout. Try reducing your scheduled habits by 20% to regain consistency."
                    }
                )
                db.add(burnout_evt)

    # Recalculate Category Balance & Rank Score
    all_cats_q = select(CategoryProgression).where(CategoryProgression.user_id == current_user.id)
    all_cats = (await db.execute(all_cats_q)).scalars().all()
    cat_levels = [c.category_level for c in all_cats]
    cat_xps = [c.category_xp for c in all_cats]
    
    lowest_cat_xp = min(cat_xps) if cat_xps else 0
    highest_cat_xp = max(cat_xps) if cat_xps else 0

    all_mastery_q = select(HabitMastery).where(HabitMastery.user_id == current_user.id)
    all_mastery = (await db.execute(all_mastery_q)).scalars().all()
    mastery_levels = [m.mastery_level for m in all_mastery]

    rank_score = calculate_rank_score(
        total_xp=user_stat.total_xp,
        consistency_90d=c90_val,
        category_levels=cat_levels,
        mastery_levels=mastery_levels,
        lowest_cat_xp=lowest_cat_xp,
        highest_cat_xp=highest_cat_xp
    )
    
    new_rank = get_rank_from_rank_score(rank_score)
    user_stat.rank = new_rank

    # Save summary
    summary = DailySummary(
        user_id=current_user.id,
        date=process_date,
        total_score_change=total_xp_change
    )
    db.add(summary)

    # Emit Progression Event
    prog_evt = ProgressionEvent(
        user_id=current_user.id,
        event_type="day_processed",
        payload={
            "completed": completed_count,
            "missed": missed_count,
            "energy": user_stat.energy_score,
            "rank": new_rank
        }
    )
    db.add(prog_evt)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"message": "Already processed", "score_change": 0, "status": "idempotent"}

    return {
        "score_change": total_xp_change,
        "new_total": user_stat.total_xp,
        "streak": user_stat.current_streak,
        "rank": user_stat.rank,
        "insight": "Perfect day! Your energy is soaring." if perfect_day else "Keep consistent to rebuild your Energy score.",
        "processed_date": process_date,
        "status": "processed"
    }
