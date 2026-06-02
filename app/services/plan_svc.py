from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import date
from app.models.user import User
from app.models.habit import Habit
from app.models.plan import Plan, PlanHabit, UserPlan
from app.schemas.habit import HabitCreate, HabitResponse
from app.schemas.plan import PlanCreate, PlanResponse
from app.core.time import get_current_time
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Habit queries (separated public / mine)
# ---------------------------------------------------------------------------

async def get_public_habits(db: AsyncSession, category: str | None = None) -> list[Habit]:
    """Return all public habits. Optionally filter by category."""
    stmt = select(Habit).where(Habit.is_public == True)
    if category:
        stmt = stmt.where(Habit.category == category)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_my_habits(db: AsyncSession, current_user: User, category: str | None = None) -> list[Habit]:
    """Return habits created by the current user."""
    stmt = select(Habit).where(Habit.created_by == current_user.id)
    if category:
        stmt = stmt.where(Habit.category == category)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_habit(db: AsyncSession, habit_data: HabitCreate, current_user: User) -> Habit:
    """Create a habit with ownership."""
    new_habit = Habit(
        name=habit_data.name,
        category=habit_data.category,
        difficulty=habit_data.difficulty,
        base_score=habit_data.base_score,
        created_by=current_user.id,
        is_public=habit_data.is_public,
    )
    db.add(new_habit)
    await db.commit()
    await db.refresh(new_habit)
    return new_habit


async def update_habit(db: AsyncSession, habit_id: int, habit_data: HabitCreate, current_user: User) -> Habit:
    """Update a habit. Only the creator can update."""
    result = await db.execute(select(Habit).where(Habit.id == habit_id))
    habit = result.scalars().first()
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")
    if habit.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your habit")

    habit.name = habit_data.name
    habit.category = habit_data.category
    habit.difficulty = habit_data.difficulty
    habit.base_score = habit_data.base_score
    habit.is_public = habit_data.is_public
    await db.commit()
    await db.refresh(habit)
    return habit


async def delete_habit(db: AsyncSession, habit_id: int, current_user: User) -> None:
    """Delete a habit. Only the creator can delete."""
    result = await db.execute(select(Habit).where(Habit.id == habit_id))
    habit = result.scalars().first()
    if not habit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")
    if habit.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your habit")

    await db.delete(habit)
    await db.commit()


# ---------------------------------------------------------------------------
# Plan queries (separated public / mine)
# ---------------------------------------------------------------------------

def _plan_with_count_stmt():
    """Build a base statement that includes habits_count as a correlated subquery."""
    count_subq = (
        select(func.count(PlanHabit.id))
        .where(PlanHabit.plan_id == Plan.id)
        .correlate(Plan)
        .scalar_subquery()
    )
    return select(Plan, count_subq.label("habits_count"))


def _rows_to_plan_dicts(rows) -> list[dict]:
    plans = []
    for plan, habits_count in rows:
        plan_dict = PlanResponse.model_validate(plan).model_dump()
        plan_dict["habits_count"] = habits_count
        plans.append(plan_dict)
    return plans


async def get_public_plans(db: AsyncSession) -> list[dict]:
    """Return public plans with habits_count."""
    stmt = _plan_with_count_stmt().where(Plan.is_public == True)
    result = await db.execute(stmt)
    return _rows_to_plan_dicts(result.all())


async def get_my_plans(db: AsyncSession, current_user: User) -> list[dict]:
    """Return plans created by the current user with habits_count."""
    stmt = _plan_with_count_stmt().where(Plan.created_by == current_user.id)
    result = await db.execute(stmt)
    return _rows_to_plan_dicts(result.all())


# ---------------------------------------------------------------------------
# Plan-scoped habits
# ---------------------------------------------------------------------------

async def get_habits_for_plan(db: AsyncSession, plan_id: int, current_user: User) -> list[Habit]:
    """
    Return all Habit objects belonging to the given plan.
    Uses selectinload to avoid N+1.
    Raises 404 if the plan does not exist.
    """
    plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_result.scalars().first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )

    # Ownership check for private plans
    if not plan.is_public and plan.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view habits of a private plan you do not own"
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
# Plan creation, update, delete
# ---------------------------------------------------------------------------

async def create_plan(db: AsyncSession, plan_data: PlanCreate, current_user: User) -> Plan:
    habit_ids = list(set(ph.habit_id for ph in plan_data.habits))
    is_public = plan_data.is_public

    if habit_ids:
        stmt = select(Habit).where(
            Habit.id.in_(habit_ids),
            (Habit.is_public == True) | (Habit.created_by == current_user.id)
        )
        result = await db.execute(stmt)
        habits = result.scalars().all()
        if len(habits) < len(habit_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more habit IDs do not exist or are not accessible")
        
        if is_public and any(not h.is_public for h in habits):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot include private habits in a public plan"
            )

    new_plan = Plan(
        name=plan_data.name,
        created_by=current_user.id,
        is_public=is_public,
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


async def update_plan(db: AsyncSession, plan_id: int, plan_data: PlanCreate, current_user: User) -> Plan:
    """Update a plan. Only the creator can update."""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if plan.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your plan")

    habit_ids = list(set(ph.habit_id for ph in plan_data.habits))
    is_public = plan_data.is_public

    if habit_ids:
        stmt = select(Habit).where(
            Habit.id.in_(habit_ids),
            (Habit.is_public == True) | (Habit.created_by == current_user.id)
        )
        result = await db.execute(stmt)
        habits = result.scalars().all()
        if len(habits) < len(habit_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more habit IDs do not exist or are not accessible")
        
        if is_public and any(not h.is_public for h in habits):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot include private habits in a public plan"
            )

    plan.name = plan_data.name
    plan.is_public = is_public
    plan.difficulty = plan_data.difficulty

    # Replace plan_habits: delete old, insert new
    old_phs = await db.execute(select(PlanHabit).where(PlanHabit.plan_id == plan.id))
    for old_ph in old_phs.scalars().all():
        await db.delete(old_ph)

    for ph in plan_data.habits:
        plan_habit = PlanHabit(
            plan_id=plan.id,
            habit_id=ph.habit_id,
            start_time=ph.start_time,
            end_time=ph.end_time,
            day_config=ph.day_config
        )
        db.add(plan_habit)

    await db.commit()
    await db.refresh(plan)
    return plan


async def delete_plan(db: AsyncSession, plan_id: int, current_user: User) -> None:
    """Delete a plan. Only the creator can delete."""
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if plan.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your plan")

    await db.delete(plan)
    await db.commit()


# ---------------------------------------------------------------------------
# Active plan system
# ---------------------------------------------------------------------------

async def activate_plan(db: AsyncSession, plan_id: int, current_user: User) -> UserPlan:
    """Deactivate all existing active plans, then activate the given plan starting today."""
    # Verify plan exists
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    # Ownership check: private plans can only be activated by their creator
    if not plan.is_public and plan.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot activate a private plan you did not create"
        )

    local_today = get_current_time(current_user.timezone).date()

    # Deactivate existing active plans
    active_result = await db.execute(
        select(UserPlan).where(UserPlan.user_id == current_user.id, UserPlan.active == True)
    )
    for p in active_result.scalars().all():
        p.active = False
        p.end_date = local_today

    # Activate new plan
    new_user_plan = UserPlan(
        user_id=current_user.id,
        plan_id=plan.id,
        active=True,
        start_date=local_today,
    )
    db.add(new_user_plan)
    await db.commit()
    await db.refresh(new_user_plan)
    logger.info(f"User {current_user.id} activated plan {plan.id} starting {local_today}")
    return new_user_plan


async def get_active_plan(db: AsyncSession, current_user: User) -> UserPlan | None:
    """Return the active UserPlan for the current user, or None."""
    result = await db.execute(
        select(UserPlan).where(UserPlan.user_id == current_user.id, UserPlan.active == True)
    )
    return result.scalars().first()
