from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import date, datetime, timedelta, time
from typing import List, Tuple
import uuid
import json

from app.models.user import User
from app.models.plan import UserPlan, PlanHabit
from app.models.habit import Habit, HabitProgressionProfile, HabitMastery
from app.models.log import DailyLog, DailySummary
from app.models.enums import HabitCategory
from app.models.scoring_version import ScoringVersion
from app.models.stat import UserStat, UserPlanStat, ScoreEvent, CategoryProgression, ProgressionEvent
from app.schemas.execution import (
    TodaysHabitResponse, LogCompletionRequest,
    TodaySummary, BackfillInfo, TodayResponse,
)
from app.core.time import get_current_time
from app.services import scoring_svc
from sqlalchemy import update, func
import asyncio
from sqlalchemy.exc import OperationalError
import logging

logger = logging.getLogger(__name__)

MAX_BACKFILL_DAYS = 7


async def _get_active_user_plan(db: AsyncSession, user: User, local_today: date) -> UserPlan | None:
    """Get the active plan for the user."""
    result = await db.execute(
        select(UserPlan).where(
            UserPlan.user_id == user.id,
            UserPlan.active == True,
        )
    )
    return result.scalars().first()


async def _auto_process_missed_days(db: AsyncSession, user: User, local_today: date) -> Tuple[int, int]:
    """
    Automatically process any missed days between the last processed date and yesterday.
    This ensures the system is reliable across server restarts and gaps.
    """
    result = await db.execute(
        select(func.max(DailySummary.date)).where(DailySummary.user_id == user.id)
    )
    last_processed = result.scalar()

    if last_processed is None:
        log_result = await db.execute(
            select(func.min(DailyLog.date)).where(DailyLog.user_id == user.id)
        )
        earliest_log = log_result.scalar()
        if earliest_log is None:
            return (0, 0)
        last_processed = earliest_log - timedelta(days=1)

    yesterday = local_today - timedelta(days=1)

    if last_processed >= yesterday:
        return (0, 0)

    total_unprocessed = (yesterday - last_processed).days
    start_date = max(last_processed + timedelta(days=1), local_today - timedelta(days=MAX_BACKFILL_DAYS))
    
    days_processed = 0
    current_date = start_date
    while current_date <= yesterday:
        logger.info(f"Auto-processing day {current_date} for user {user.id}")
        await scoring_svc.process_day(db, user, current_date)
        days_processed += 1
        current_date += timedelta(days=1)

    remaining = max(0, total_unprocessed - days_processed)
    return (days_processed, remaining)


init_lock = asyncio.Lock()

async def initialize_logs_for_today(db: AsyncSession, current_user: User, local_today: date) -> List[DailyLog]:
    """Generates immutable DailyLog records based on the active UserPlan for today if not present."""
    async with init_lock:
        active_user_plan = await _get_active_user_plan(db, current_user, local_today)
        
        if not active_user_plan:
            return []
            
        plan_id = active_user_plan.plan_id
        
        # Get existing logs
        logs_query = select(DailyLog).where(
            DailyLog.user_id == current_user.id,
            DailyLog.date == local_today,
            DailyLog.plan_id == plan_id
        )
        logs_result = await db.execute(logs_query)
        existing_logs = logs_result.scalars().all()
        
        if existing_logs:
            return existing_logs
            
        # Get active scoring version
        version_q = select(ScoringVersion).where(ScoringVersion.is_active == True)
        version_res = await db.execute(version_q)
        active_version = version_res.scalars().first()
        scoring_ver = active_version.id if active_version else "v1"
        if active_version:
            formula_snap = {
                "id": active_version.id,
                "formula_name": active_version.formula_name,
                "formula_code": active_version.formula_code,
                "parameters": active_version.parameters
            }
        else:
            formula_snap = {
                "id": "v1",
                "formula_name": "original_v1",
                "parameters": {}
            }

        # Generate new logs from plan mapping
        ph_query = select(PlanHabit).where(PlanHabit.plan_id == plan_id)
        ph_result = await db.execute(ph_query)
        plan_habits = ph_result.scalars().all()
        
        today_weekday = local_today.weekday()
        
        new_logs = []
        for ph in plan_habits:
            day_cfg = (ph.day_config or "everyday").lower().strip()
            if day_cfg == "weekdays" and today_weekday > 4:
                continue
            if day_cfg == "weekends" and today_weekday < 5:
                continue
                
            h_query = select(Habit).where(Habit.id == ph.habit_id)
            h_result = await db.execute(h_query)
            habit = h_result.scalars().first()
            
            if not habit: continue
            
            # Snapshots of progression profiles
            active_prof = habit.active_profile
            profile_snap = None
            prof_id = None
            if active_prof:
                prof_id = active_prof.id
                profile_snap = {
                    "difficulty": active_prof.difficulty_coefficient,
                    "difficulty_coefficient": active_prof.difficulty_coefficient,
                    "frequency": active_prof.frequency,
                    "type": active_prof.habit_type,
                    "habit_type": active_prof.habit_type,
                    "estimated_duration_minutes": active_prof.estimated_duration_minutes
                }

            log = DailyLog(
                user_id=current_user.id,
                plan_id=plan_id,
                habit_id=habit.id,
                snapshot_habit_name=habit.name,
                category=habit.category,
                snapshot_difficulty=habit.difficulty,
                snapshot_base_score=habit.base_score,
                date=local_today,
                status="pending",
                awarded_points=0,
                # v2 Progression fields
                scoring_version=scoring_ver,
                profile_id=prof_id,
                profile_snapshot_json=profile_snap,
                formula_snapshot_json=formula_snap
            )
            db.add(log)
            new_logs.append(log)
            
        try:
            await db.commit()
            for log in new_logs:
                await db.refresh(log)
        except IntegrityError:
            await db.rollback()
            logs_result = await db.execute(logs_query)
            return logs_result.scalars().all()
            
        return new_logs


def _build_live_summary(logs: List[DailyLog]) -> TodaySummary:
    """Compute a live preview of today's progress from current log state."""
    total = len(logs)
    completed = sum(1 for l in logs if l.status == "done")
    missed = sum(1 for l in logs if l.status == "missed")
    pending = sum(1 for l in logs if l.status == "pending")
    earned = sum(l.awarded_points for l in logs if l.status == "done")
    possible = sum(l.snapshot_base_score for l in logs)
    pct = (completed / total * 100) if total > 0 else 0.0

    return TodaySummary(
        total_tasks=total,
        completed=completed,
        pending=pending,
        missed=missed,
        earned_points=earned,
        earned_xp=earned,
        possible_points=possible,
        possible_xp=possible,
        completion_pct=round(pct, 1),
    )


async def get_today_data(db: AsyncSession, current_user: User) -> TodayResponse:
    """Main entry point for GET /today."""
    local_today = get_current_time(current_user.timezone).date()
    days_processed, remaining = await _auto_process_missed_days(db, current_user, local_today)
    logs = await initialize_logs_for_today(db, current_user, local_today)
    
    tasks = []
    for log in logs:
        tasks.append(TodaysHabitResponse(
            id=log.id,
            habit_id=log.habit_id,
            name=log.snapshot_habit_name,
            category=log.category,
            difficulty=log.snapshot_difficulty,
            base_score=log.snapshot_base_score,
            base_xp=log.snapshot_base_score,
            status=log.status,
            awarded_points=log.awarded_points,
            awarded_xp=log.awarded_points,
            completion_timestamp=log.completion_timestamp,
        ))

    return TodayResponse(
        tasks=tasks,
        summary=_build_live_summary(logs),
        backfill=BackfillInfo(
            missed_days_processed=days_processed,
            remaining_unprocessed_days=remaining,
        ),
    )


async def mark_habit_completed(db: AsyncSession, request: LogCompletionRequest, current_user: User) -> DailyLog:
    ct = get_current_time(current_user.timezone)
    local_today = ct.date()
    
    # Pre-flight query to get the log, start/end times, and configurable grace period
    query = select(DailyLog, PlanHabit.start_time, PlanHabit.end_time, PlanHabit.grace_period_minutes, PlanHabit.late_threshold_minutes).join(
        PlanHabit, (PlanHabit.plan_id == DailyLog.plan_id) & (PlanHabit.habit_id == DailyLog.habit_id), isouter=True
    ).where(
        DailyLog.user_id == current_user.id,
        DailyLog.habit_id == request.habit_id,
        DailyLog.date == local_today
    )
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit log for today not found")
        
    log, start_time, end_time, grace_mins, late_mins = row

    if log.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already completed or processed")

    # Fetch UserStat to read current rank, energy, recovery tokens, etc.
    stat_q = select(UserStat).where(UserStat.user_id == current_user.id)
    user_stat = (await db.execute(stat_q)).scalars().first()
    if not user_stat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User stats not found")

    # 1. Scoring Logic version check
    if log.scoring_version == "v1":
        # Legacy scoring logic
        late_flag = False
        if end_time and ct.time() > end_time:
            late_flag = True
        points = log.snapshot_base_score // 2 if late_flag else log.snapshot_base_score
        
        stmt = (
            update(DailyLog)
            .where(
                DailyLog.id == log.id,
                DailyLog.user_id == current_user.id,
                DailyLog.status == "pending"
            )
            .values(
                status="done",
                awarded_points=points,
                completion_timestamp=ct,
                late_flag=late_flag,
                note=request.note
            )
        )
        update_result = await db.execute(stmt)
        if update_result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already completed or processed")
        
        # Update local ORM state
        log.status = "done"
        log.awarded_points = points
        log.completion_timestamp = ct
        log.late_flag = late_flag
        log.note = request.note
        
        await db.commit()
        await db.refresh(log)
        return log

    # --- v2 Progression Engine Scoring ---
    grace_mins = grace_mins if grace_mins is not None else 15
    late_mins = late_mins if late_mins is not None else 120

    # Lateness & Quality calculation
    quality_mult = 1.0
    late_flag = False
    
    if end_time:
        comp_time = ct.time()
        # Scheduled window bounds
        sched_start = start_time if start_time else time(0, 0, 0)
        
        # Convert to datetime to perform calculations with duration additions cleanly
        base_d = datetime.combine(local_today, end_time)
        comp_d = datetime.combine(local_today, comp_time)
        start_d = datetime.combine(local_today, sched_start)
        
        if comp_d < start_d - timedelta(minutes=30):
            # Early completion
            quality_mult = 1.1
        elif comp_d <= base_d:
            # On-time completion
            quality_mult = 1.0
        elif comp_d <= base_d + timedelta(minutes=grace_mins):
            # Grace period
            quality_mult = 0.9
        elif comp_d <= base_d + timedelta(minutes=late_mins):
            # Late completion
            quality_mult = 0.5
            late_flag = True
        else:
            # Very late completion
            quality_mult = 0.25
            late_flag = True

    # 30-Day Consistency Multiplier for this specific habit
    start_30d = local_today - timedelta(days=30)
    c30_q = select(DailyLog).where(
        DailyLog.user_id == current_user.id,
        DailyLog.habit_id == request.habit_id,
        DailyLog.date >= start_30d,
        DailyLog.date < local_today,
        DailyLog.status.in_(["done", "missed"])
    )
    history_logs = (await db.execute(c30_q)).scalars().all()
    if history_logs:
        done_count = sum(1 for l in history_logs if l.status == "done")
        c30_val = done_count / len(history_logs)
    else:
        c30_val = 1.0 # default to perfect consistency if no history
        
    consistency_mult = 0.8 + (0.4 * c30_val)

    # Mastery level lookup
    mastery_q = select(HabitMastery).where(
        HabitMastery.user_id == current_user.id,
        HabitMastery.habit_id == request.habit_id
    )
    mastery_rec = (await db.execute(mastery_q)).scalars().first()
    mastery_level = mastery_rec.mastery_level if mastery_rec else 1
    mastery_bonus = mastery_level // 5

    # BaseXP dynamically stored in daily log snapshot base score
    base_xp = log.snapshot_base_score
    
    # Calculate effective score
    effective_score = round(base_xp * quality_mult * consistency_mult) + mastery_bonus

    # Calculate Energy Multiplier
    energy_mult = 0.9 + 0.2 * (user_stat.energy_score / 100.0)
    xp_gained = round(effective_score * energy_mult)

    # Dynamic Daily XP Cap Check
    rank_lv = scoring_svc.get_rank_level(user_stat.rank)
    daily_cap = scoring_svc.get_daily_xp_cap(rank_lv)
    
    # Sum XP earned today
    today_xp_q = select(func.sum(DailyLog.awarded_points)).where(
        DailyLog.user_id == current_user.id,
        DailyLog.date == local_today,
        DailyLog.status == "done"
    )
    today_xp_earned = (await db.execute(today_xp_q)).scalar() or 0
    
    if today_xp_earned + xp_gained > daily_cap:
        xp_gained = max(0, daily_cap - today_xp_earned)

    # Update DailyLog record atomically to prevent concurrency race conditions
    stmt = (
        update(DailyLog)
        .where(
            DailyLog.id == log.id,
            DailyLog.user_id == current_user.id,
            DailyLog.status == "pending"
        )
        .values(
            status="done",
            awarded_points=xp_gained,
            completion_timestamp=ct,
            late_flag=late_flag,
            note=request.note,
            quality_multiplier=quality_mult,
            consistency_multiplier=consistency_mult,
            mastery_bonus=mastery_bonus
        )
    )
    update_result = await db.execute(stmt)
    if update_result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already completed or processed")
    
    # Update local ORM object state
    log.status = "done"
    log.awarded_points = xp_gained
    log.completion_timestamp = ct
    log.late_flag = late_flag
    log.note = request.note
    log.quality_multiplier = quality_mult
    log.consistency_multiplier = consistency_mult
    log.mastery_bonus = mastery_bonus

    # Update UserStat Experience
    old_xp = user_stat.total_xp
    user_stat.total_xp += xp_gained
    user_stat.lifetime_xp += xp_gained
    new_xp = user_stat.total_xp

    # Update Category Splits in stats (backward compatible)
    if log.category == HabitCategory.focus:
        user_stat.focus_points += xp_gained
    elif log.category == HabitCategory.health:
        user_stat.health_points += xp_gained
    elif log.category == HabitCategory.discipline:
        user_stat.discipline_points += xp_gained
    elif log.category == HabitCategory.mind:
        user_stat.mind_points += xp_gained

    # Adjust Energy (done habit gives +5 energy, cap at 100)
    user_stat.energy_score = min(100, user_stat.energy_score + 5)

    # Update CategoryProgression
    cat_prog_q = select(CategoryProgression).where(
        CategoryProgression.user_id == current_user.id,
        CategoryProgression.category == log.category
    )
    cat_prog = (await db.execute(cat_prog_q)).scalars().first()
    if not cat_prog:
        cat_prog = CategoryProgression(user_id=current_user.id, category=log.category, category_xp=0, category_level=1)
        db.add(cat_prog)
    cat_prog.category_xp += xp_gained
    
    # Re-evaluate category level boundary: req = 250 * level^1.6
    while True:
        req = int(250 * (cat_prog.category_level ** 1.6))
        if cat_prog.category_xp >= req:
            cat_prog.category_level += 1
        else:
            break

    # Update HabitMastery
    if not mastery_rec and log.habit_id is not None:
        mastery_rec = HabitMastery(user_id=current_user.id, habit_id=log.habit_id, times_completed=0, total_time_spent=0, mastery_xp=0, mastery_level=1)
        db.add(mastery_rec)
        
    if mastery_rec:
        mastery_rec.times_completed += 1
        duration_snap = 15
        if log.profile_snapshot_json:
            try:
                if isinstance(log.profile_snapshot_json, str):
                    snap_data = json.loads(log.profile_snapshot_json)
                else:
                    snap_data = log.profile_snapshot_json
                duration_snap = snap_data.get("estimated_duration_minutes", 15)
            except Exception:
                pass
        mastery_rec.total_time_spent += duration_snap
        mastery_rec.mastery_xp += xp_gained
        mastery_rec.last_completed_at = ct
        
        # Re-evaluate mastery level boundary: req = 100 * level^1.8
        while True:
            req = int(100 * (mastery_rec.mastery_level ** 1.8))
            if mastery_rec.mastery_xp >= req:
                mastery_rec.mastery_level += 1
            else:
                break

    # Recalculate 90-Day rolling consistency for rank
    start_90d = local_today - timedelta(days=90)
    c90_q = select(DailyLog).where(
        DailyLog.user_id == current_user.id,
        DailyLog.date >= start_90d,
        DailyLog.date <= local_today,
        DailyLog.status.in_(["done", "missed"])
    )
    logs_90d = (await db.execute(c90_q)).scalars().all()
    if logs_90d:
        done_90 = sum(1 for l in logs_90d if l.status == "done")
        c90_val = done_90 / len(logs_90d)
    else:
        c90_val = 1.0

    user_stat.consistency_7d = 1.0 # placeholder / dynamic calculations if needed
    user_stat.consistency_30d = c30_val
    user_stat.consistency_90d = c90_val

    # Recalculate Rank Score
    # Fetch all category progressions for user
    all_cats_q = select(CategoryProgression).where(CategoryProgression.user_id == current_user.id)
    all_cats = (await db.execute(all_cats_q)).scalars().all()
    cat_levels = [c.category_level for c in all_cats]
    
    # Safeguard Lowest / Highest Category XP Division-by-Zero
    cat_xps = [c.category_xp for c in all_cats]
    lowest_cat_xp = min(cat_xps) if cat_xps else 0
    highest_cat_xp = max(cat_xps) if cat_xps else 0

    all_mastery_q = select(HabitMastery).where(HabitMastery.user_id == current_user.id)
    all_mastery = (await db.execute(all_mastery_q)).scalars().all()
    mastery_levels = [m.mastery_level for m in all_mastery]

    rank_score = scoring_svc.calculate_rank_score(
        total_xp=new_xp,
        consistency_90d=c90_val,
        category_levels=cat_levels,
        mastery_levels=mastery_levels,
        lowest_cat_xp=lowest_cat_xp,
        highest_cat_xp=highest_cat_xp
    )

    new_rank = scoring_svc.get_rank_from_rank_score(rank_score)
    user_stat.rank = new_rank

    # Update UserPlanStat
    if log.plan_id:
        plan_stat_q = select(UserPlanStat).where(
            UserPlanStat.user_id == current_user.id,
            UserPlanStat.plan_id == log.plan_id
        )
        plan_stat = (await db.execute(plan_stat_q)).scalars().first()
        if plan_stat:
            plan_stat.total_xp += xp_gained
            if log.category == HabitCategory.focus:
                plan_stat.focus_points += xp_gained
            elif log.category == HabitCategory.health:
                plan_stat.health_points += xp_gained
            elif log.category == HabitCategory.discipline:
                plan_stat.discipline_points += xp_gained
            elif log.category == HabitCategory.mind:
                plan_stat.mind_points += xp_gained

    # Score Audit Trail Log
    evt_id = str(uuid.uuid4())
    score_evt = ScoreEvent(
        event_id=evt_id,
        user_id=current_user.id,
        date=local_today,
        event_type="habit_completed",
        old_xp=old_xp,
        delta_xp=xp_gained,
        new_xp=new_xp,
        reason=f"Completed habit: {log.snapshot_habit_name}",
        metadata_json={
            "habit_id": log.habit_id,
            "quality_multiplier": quality_mult,
            "consistency_multiplier": consistency_mult,
            "mastery_bonus": mastery_bonus
        }
    )
    db.add(score_evt)

    # Event Sourcing Progression Event
    prog_evt = ProgressionEvent(
        user_id=current_user.id,
        event_type="habit_completed",
        payload={
            "habit_id": log.habit_id,
            "xp_gained": xp_gained,
            "quality": quality_mult,
            "rank": new_rank
        }
    )
    db.add(prog_evt)

    await db.commit()
    await db.refresh(log)
    return log


async def manual_process_day(db: AsyncSession, current_user: User) -> dict:
    """Manual trigger for POST /today/process."""
    local_today = get_current_time(current_user.timezone).date()
    process_date = local_today
    return await scoring_svc.process_day(db, current_user, process_date)
