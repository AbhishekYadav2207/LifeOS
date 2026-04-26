from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.responses import BaseResponse
from app.schemas.habit import HabitCreate, HabitResponse
from app.schemas.plan import PlanCreate, PlanResponse, SelectPlanRequest
from app.services import plan_svc

router = APIRouter(prefix="/plans", tags=["Plans & Habits"])


# ---------------------------------------------------------------------------
# Habits catalog  (MUST be defined before /{plan_id}/habits to avoid routing
# conflict where FastAPI would match "habits" as a plan_id value)
# ---------------------------------------------------------------------------

@router.get(
    "/habits",
    response_model=BaseResponse[List[HabitResponse]],
    summary="List all habits (global catalog)",
    description="Returns every habit in the system. Optionally filter by category.",
)
async def list_habits(
    category: Optional[str] = Query(None, description="Filter by habit category (e.g. health, mind, focus, discipline)"),
    db: AsyncSession = Depends(get_db),
):
    habits = await plan_svc.get_all_habits(db, category=category)
    return BaseResponse(success=True, data=habits)


@router.post(
    "/habits",
    response_model=BaseResponse[HabitResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new habit",
)
async def create_habit(
    habit_data: HabitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    habit = await plan_svc.create_habit(db, habit_data)
    return BaseResponse(success=True, data=habit, message="Habit created")


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=BaseResponse[List[PlanResponse]],
    summary="List public plans",
    description="Returns all public plans. Each plan includes a habits_count but NOT the full habit list.",
)
async def list_public_plans(db: AsyncSession = Depends(get_db)):
    plans = await plan_svc.get_public_plans(db)
    return BaseResponse(success=True, data=plans)


@router.post(
    "/",
    response_model=BaseResponse[PlanResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new plan",
)
async def create_plan(
    plan_data: PlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await plan_svc.create_plan(db, plan_data, current_user)
    return BaseResponse(success=True, data=PlanResponse.model_validate(plan), message="Plan created")


@router.post(
    "/select-plan",
    response_model=BaseResponse,
    summary="Assign a plan to the current user",
)
async def select_plan(
    request: SelectPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_plan = await plan_svc.assign_plan_to_user(db, request, current_user)
    return BaseResponse(
        success=True,
        message=f"Plan applied successfully. It will be active starting {user_plan.start_date}",
    )


# ---------------------------------------------------------------------------
# Plan-scoped habits  (nested resource endpoint)
# ---------------------------------------------------------------------------

@router.get(
    "/{plan_id}/habits",
    response_model=BaseResponse[List[HabitResponse]],
    summary="Get habits for a specific plan",
    description=(
        "Returns all habits belonging to the given plan. "
        "Uses selectinload to avoid N+1 queries. "
        "Returns 404 if the plan does not exist."
    ),
)
async def list_plan_habits(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
):
    habits = await plan_svc.get_habits_for_plan(db, plan_id)
    return BaseResponse(
        success=True,
        data=habits,
        message=f"{len(habits)} habit(s) found for plan {plan_id}",
    )
