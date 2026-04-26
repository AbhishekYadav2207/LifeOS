from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import date, datetime, timedelta
from typing import List, Tuple

from app.models.user import User
from app.models.plan import UserPlan, PlanHabit
from app.models.habit import Habit
from app.models.log import DailyLog, DailySummary
from app.schemas.execution import (
    TodaysHabitResponse, LogCompletionRequest,
    TodaySummary, BackfillInfo, TodayResponse,
)
from app.core.time import get_current_time, get_local_today
from app.services import scoring_svc
from sqlalchemy import update, func
import asyncio
from sqlalchemy.exc import OperationalError
import logging

logger = logging.getLogger(__name__)

MAX_BACKFILL_DAYS = 7


async def _get_active_user_plan(db: AsyncSession, user: User, local_today: date) -> UserPlan | None:
    """Get the active plan for the user that has started on or before today."""
    result = await db.execute(
        select(UserPlan).where(
            UserPlan.user_id == user.id,
            UserPlan.active == True,
            UserPlan.start_date <= local_today,
        )
    )
    return result.scalars().first()


async def _auto_process_missed_days(db: AsyncSession, user: User, local_today: date) -> Tuple[int, int]:
    """
    Automatically process any missed days between the last processed date and yesterday.
    This ensures the system is reliable across server restarts and gaps.
    
    Only processes up to MAX_BACKFILL_DAYS to avoid heavy loops.
    Processes previous day(s), never today.
    
    Returns:
        (days_processed, remaining_unprocessed) for transparency in the response.
    """
    # Find the last processed date for this user
    result = await db.execute(
        select(func.max(DailySummary.date)).where(DailySummary.user_id == user.id)
    )
    last_processed = result.scalar()

    # Find the earliest log date if no summary exists yet
    if last_processed is None:
        log_result = await db.execute(
            select(func.min(DailyLog.date)).where(DailyLog.user_id == user.id)
        )
        earliest_log = log_result.scalar()
        if earliest_log is None:
            return (0, 0)  # No logs exist at all, nothing to backfill
        last_processed = earliest_log - timedelta(days=1)

    yesterday = local_today - timedelta(days=1)

    if last_processed >= yesterday:
        return (0, 0)  # Nothing to process

    # Calculate total unprocessed days
    total_unprocessed = (yesterday - last_processed).days

    # Limit backfill range
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


async def initialize_logs_for_today(db: AsyncSession, current_user: User, local_today: date) -> List[DailyLog]:
    """Generates immutable DailyLog records based on the active UserPlan for today if not present."""
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
        
    # Generate new logs from plan mapping
    ph_query = select(PlanHabit).where(PlanHabit.plan_id == plan_id)
    ph_result = await db.execute(ph_query)
    plan_habits = ph_result.scalars().all()
    
    new_logs = []
    for ph in plan_habits:
        h_query = select(Habit).where(Habit.id == ph.habit_id)
        h_result = await db.execute(h_query)
        habit = h_result.scalars().first()
        
        if not habit: continue
        
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
            awarded_points=0
        )
        db.add(log)
        new_logs.append(log)
        
    try:
        await db.commit()
        for log in new_logs:
            await db.refresh(log)
    except IntegrityError:
        # Handling the race condition if parallel requests initialized logs simultaneously
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
        possible_points=possible,
        completion_pct=round(pct, 1),
    )


async def get_today_data(db: AsyncSession, current_user: User) -> TodayResponse:
    """
    Main entry point for GET /today.
    
    1. Resolve local today using user's timezone
    2. Auto-process any missed past days
    3. Initialize today's logs
    4. Return tasks + live summary + backfill info
    """
    local_today = get_local_today(current_user.timezone)

    # Auto-process missed days before returning today's data
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
            status=log.status,
            awarded_points=log.awarded_points,
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
    
    # Pre-flight query to get the ID and static properties
    query = select(DailyLog, PlanHabit.end_time).join(
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
        
    log, end_time = row
    
    # Late detection: both ct.time() and end_time are naive times in the user's local timezone.
    # ct was created from get_current_time(user.timezone), so ct.time() is the local wall-clock time.
    # end_time is stored as a naive Time from the plan — intended to represent local user time.
    late_flag = False
    if end_time and ct.time() > end_time:
        late_flag = True
        
    points = log.snapshot_base_score // 2 if late_flag else log.snapshot_base_score

    # Atomic Update Layer with explicit retry
    max_retries = 2
    for attempt in range(max_retries):
        try:
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
                await db.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already completed or invalid")
                
            await db.commit()
            await db.refresh(log)
            return log
        except OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                await db.rollback()
                await asyncio.sleep(0.1)
                continue
            raise e


async def manual_process_day(db: AsyncSession, current_user: User) -> dict:
    """
    Manual trigger for POST /today/process.
    Processes the previous day using the user's timezone.
    """
    local_today = get_local_today(current_user.timezone)
    process_date = local_today - timedelta(days=1)
    return await scoring_svc.process_day(db, current_user, process_date)
