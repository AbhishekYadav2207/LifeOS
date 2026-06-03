from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.responses import BaseResponse
from app.schemas.plan import PlanCreate, PlanResponse
from app.schemas.habit import HabitResponse, PlanHabitTimelineResponse
from app.services import plan_svc

router = APIRouter(prefix="/plans", tags=["Plans"])


# ---------------------------------------------------------------------------
# Plan listing (separated public / mine)
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=BaseResponse[List[PlanResponse]],
    summary="List public plans",
    description="Returns all public plans with habits_count.",
)
async def list_public_plans(db: AsyncSession = Depends(get_db)):
    plans = await plan_svc.get_public_plans(db)
    return BaseResponse(success=True, data=plans)


@router.get(
    "/mine",
    response_model=BaseResponse[List[PlanResponse]],
    summary="List my plans",
    description="Returns plans created by the current user.",
)
async def list_my_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plans = await plan_svc.get_my_plans(db, current_user)
    return BaseResponse(success=True, data=plans)


# ---------------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=BaseResponse[PlanResponse],
    summary="Create a new plan",
)
async def create_plan(
    plan_data: PlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await plan_svc.create_plan(db, plan_data, current_user)
    return BaseResponse(success=True, data=PlanResponse.model_validate(plan), message="Plan created")


@router.put(
    "/{plan_id}",
    response_model=BaseResponse[PlanResponse],
    summary="Update a plan",
)
async def update_plan(
    plan_id: int,
    plan_data: PlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = await plan_svc.update_plan(db, plan_id, plan_data, current_user)
    return BaseResponse(success=True, data=PlanResponse.model_validate(plan), message="Plan updated")


@router.delete(
    "/{plan_id}",
    response_model=BaseResponse,
    summary="Delete a plan",
)
async def delete_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await plan_svc.delete_plan(db, plan_id, current_user)
    return BaseResponse(success=True, message="Plan deleted")


# ---------------------------------------------------------------------------
# Plan activation
# ---------------------------------------------------------------------------

@router.post(
    "/{plan_id}/activate",
    response_model=BaseResponse,
    summary="Activate a plan for the current user",
    description="Deactivates all existing active plans and activates the given plan starting today.",
)
async def activate_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_plan = await plan_svc.activate_plan(db, plan_id, current_user)
    return BaseResponse(
        success=True,
        message=f"Plan activated successfully. Active starting {user_plan.start_date}",
    )


# ---------------------------------------------------------------------------
# Plan-scoped habits (nested resource)
# ---------------------------------------------------------------------------

@router.get(
    "/{plan_id}/habits",
    response_model=BaseResponse[List[PlanHabitTimelineResponse]],
    summary="Get habits for a specific plan",
    description=(
        "Returns all habits belonging to the given plan if public or owned by the user. "
        "Uses selectinload to avoid N+1 queries. "
        "Returns 404 if the plan does not exist."
    ),
)
async def list_plan_habits(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    habits = await plan_svc.get_habits_for_plan(db, plan_id, current_user)
    return BaseResponse(
        success=True,
        data=habits,
        message=f"{len(habits)} habit(s) found for plan {plan_id}",
    )
