from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import date, timedelta
from app.models.user import User
from app.models.habit import Habit
from app.models.plan import Plan, PlanHabit, UserPlan
from app.schemas.habit import HabitCreate, HabitResponse
from app.schemas.plan import PlanCreate, PlanResponse, SelectPlanRequest
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Habit catalog (global, unscoped)
# ---------------------------------------------------------------------------

async def get_all_habits(db: AsyncSession, category: str | None = None) -> list[Habit]:
    """Return all habits in the system. Optionally filter by category."""
    stmt = select(Habit)
    if category:
        stmt = stmt.where(Habit.category == category)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_habit(db: AsyncSession, habit_data: HabitCreate) -> Habit:
    new_habit = Habit(**habit_data.model_dump())
    db.add(new_habit)
    await db.commit()
    await db.refresh(new_habit)
    return new_habit


# ---------------------------------------------------------------------------
# Plan listing (lightweight — no nested habits)
# ---------------------------------------------------------------------------

async def get_public_plans(db: AsyncSession) -> list[dict]:
    """
    Return public plans with a habits_count scalar subquery.
    Avoids N+1: a single SQL query fetches plans + counts in one shot.
    """
    count_subq = (
        select(func.count(PlanHabit.id))
        .where(PlanHabit.plan_id == Plan.id)
        .correlate(Plan)
        .scalar_subquery()
    )

    stmt = select(Plan, count_subq.label("habits_count")).where(Plan.is_public == True)
    result = await db.execute(stmt)
    rows = result.all()

    plans = []
    for plan, habits_count in rows:
        plan_dict = PlanResponse.model_validate(plan).model_dump()
        plan_dict["habits_count"] = habits_count
        plans.append(plan_dict)

    return plans


# ---------------------------------------------------------------------------
# Plan-scoped habits (main relationship endpoint)
# ---------------------------------------------------------------------------

async def get_habits_for_plan(db: AsyncSession, plan_id: int) -> list[Habit]:
    """
    Return all Habit objects belonging to the given plan.

    Uses selectinload to avoid N+1:
      Query 1 → fetch PlanHabit rows for plan_id
      Query 2 → fetch all related Habit rows in a single IN clause
    Raises 404 if the plan does not exist.
    """
    # Verify plan exists first
    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_result.scalars().first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )

    stmt = (
        select(PlanHabit)
        .where(PlanHabit.plan_id == plan_id)
        .options(selectinload(PlanHabit.habit))
    )
    result = await db.execute(stmt)
    plan_habits = result.scalars().all()

    return [ph.habit for ph in plan_habits]


# ---------------------------------------------------------------------------
# Plan creation & user assignment
# ---------------------------------------------------------------------------

async def create_plan(db: AsyncSession, plan_data: PlanCreate, current_user: User) -> Plan:
    new_plan = Plan(
        name=plan_data.name,
        created_by=current_user.id,
        is_public=plan_data.is_public,
        difficulty=plan_data.difficulty
    )
    db.add(new_plan)
    await db.flush()
    await db.refresh(new_plan)

    for ph in plan_data.habits:
        plan_habit = PlanHabit(
            plan_id=new_plan.id,
            habit_id=ph.habit_id,
            start_time=ph.start_time,
            end_time=ph.end_time,
            day_config=ph.day_config
        )
        db.add(plan_habit)

    await db.commit()
    await db.refresh(new_plan)
    return new_plan


async def assign_plan_to_user(db: AsyncSession, request: SelectPlanRequest, current_user: User) -> UserPlan:
    # 1. Verify Plan exists
    result = await db.execute(select(Plan).where(Plan.id == request.plan_id))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    # 2. End current active plan for user
    active_plans = await db.execute(
        select(UserPlan).where(UserPlan.user_id == current_user.id, UserPlan.active == True)
    )
    for p in active_plans.scalars().all():
        p.active = False

    # 3. Create new user plan mapping, starting tomorrow by default
    start_dt = request.start_date or (date.today() + timedelta(days=1))

    new_user_plan = UserPlan(
        user_id=current_user.id,
        plan_id=plan.id,
        active=True,
        start_date=start_dt
    )
    db.add(new_user_plan)
    await db.commit()
    await db.refresh(new_user_plan)
    logger.info(f"User {current_user.id} assigned to plan {plan.id} starting {start_dt}")
    return new_user_plan
