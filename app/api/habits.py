from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy.future import select
from app.models.habit import Habit

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.responses import BaseResponse
from app.schemas.habit import HabitCreate, HabitResponse
from app.services import plan_svc

router = APIRouter(prefix="/plans/habits", tags=["Habits"])


# ---------------------------------------------------------------------------
# Habit listing (separated public / mine)
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=BaseResponse[List[HabitResponse]],
    summary="List all habits",
    description="Returns all habits.",
)
async def list_habits(
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Habit)
    result = await db.execute(stmt)
    habits = result.scalars().all()
    return BaseResponse(success=True, data=habits)

@router.get(
    "/public",
    response_model=BaseResponse[List[HabitResponse]],
    summary="List public habits",
    description="Returns all public habits. Optionally filter by category.",
)
async def list_public_habits(
    category: Optional[str] = Query(None, description="Filter by habit category"),
    db: AsyncSession = Depends(get_db),
):
    habits = await plan_svc.get_public_habits(db, category=category)
    return BaseResponse(success=True, data=habits)


@router.get(
    "/mine",
    response_model=BaseResponse[List[HabitResponse]],
    summary="List my habits",
    description="Returns habits created by the current user. Optionally filter by category.",
)
async def list_my_habits(
    category: Optional[str] = Query(None, description="Filter by habit category"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    habits = await plan_svc.get_my_habits(db, current_user, category=category)
    return BaseResponse(success=True, data=habits)


# ---------------------------------------------------------------------------
# Habit CRUD
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=BaseResponse[HabitResponse],
    summary="Create a new habit",
)
async def create_habit(
    habit_data: HabitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    habit = await plan_svc.create_habit(db, habit_data, current_user)
    return BaseResponse(success=True, data=habit, message="Habit created")


@router.put(
    "/{habit_id}",
    response_model=BaseResponse[HabitResponse],
    summary="Update a habit",
)
async def update_habit(
    habit_id: int,
    habit_data: HabitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    habit = await plan_svc.update_habit(db, habit_id, habit_data, current_user)
    return BaseResponse(success=True, data=habit, message="Habit updated")


@router.delete(
    "/{habit_id}",
    response_model=BaseResponse,
    summary="Delete a habit",
)
async def delete_habit(
    habit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await plan_svc.delete_habit(db, habit_id, current_user)
    return BaseResponse(success=True, message="Habit deleted")
