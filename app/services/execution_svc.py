from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import date, datetime, timezone
from typing import List

from app.models.user import User
from app.models.plan import UserPlan, PlanHabit
from app.models.habit import Habit
from app.models.log import DailyLog
from app.schemas.execution import TodaysHabitResponse, LogCompletionRequest

async def initialize_logs_for_today(db: AsyncSession, current_user: User, local_today: date) -> List[DailyLog]:
    """Generates immutable DailyLog records based on the active UserPlan for today if not present."""
    # Find active plan started on or before today
    plan_query = select(UserPlan).where(
        UserPlan.user_id == current_user.id,
        UserPlan.active == True,
        UserPlan.start_date <= local_today
    )
    result = await db.execute(plan_query)
    active_user_plan = result.scalars().first()
    
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
        
    # Generate new logs from plan
    ph_query = select(PlanHabit).where(PlanHabit.plan_id == plan_id)
    ph_result = await db.execute(ph_query)
    plan_habits = ph_result.scalars().all()
    
    new_logs = []
    for ph in plan_habits:
        # Get actual habit details to snapshot
        h_query = select(Habit).where(Habit.id == ph.habit_id)
        h_result = await db.execute(h_query)
        habit = h_result.scalars().first()
        
        if not habit: continue
        
        log = DailyLog(
            user_id=current_user.id,
            plan_id=plan_id,
            habit_id=habit.id,
            snapshot_habit_name=habit.name,
            snapshot_category=habit.category,
            snapshot_difficulty=habit.difficulty,
            snapshot_base_score=habit.base_score,
            date=local_today,
            status="pending"
        )
        db.add(log)
        new_logs.append(log)
        
    await db.commit()
    return new_logs

async def get_today_logs(db: AsyncSession, current_user: User) -> List[TodaysHabitResponse]:
    local_today = datetime.now(timezone.utc).date() # For simplicity in V1, assuming UTC execution context
    logs = await initialize_logs_for_today(db, current_user, local_today)
    
    responses = []
    for log in logs:
        responses.append(TodaysHabitResponse(
            id=log.id,
            habit_id=log.habit_id,
            name=log.snapshot_habit_name,
            category=log.snapshot_category,
            difficulty=log.snapshot_difficulty,
            base_score=log.snapshot_base_score,
            status=log.status,
            completion_timestamp=log.completion_timestamp
        ))
    return responses

async def mark_habit_completed(db: AsyncSession, request: LogCompletionRequest, current_user: User) -> DailyLog:
    local_today = datetime.now(timezone.utc).date()
    
    query = select(DailyLog).where(
        DailyLog.user_id == current_user.id,
        DailyLog.habit_id == request.habit_id,
        DailyLog.date == local_today
    )
    result = await db.execute(query)
    log = result.scalars().first()
    
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit log for today not found")
        
    if log.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Habit already processed")
        
    log.status = "done"
    log.completion_timestamp = datetime.now(timezone.utc)
    log.note = request.note
    
    # Very simple late heuristic for V1: after 8 PM UTC is late
    if log.completion_timestamp.hour >= 20: 
        log.late_flag = True
        
    await db.commit()
    await db.refresh(log)
    return log
