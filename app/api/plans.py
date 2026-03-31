from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.responses import BaseResponse
from app.schemas.habit import HabitCreate, HabitResponse
from app.schemas.plan import PlanCreate, PlanResponse, SelectPlanRequest
from app.services import plan_svc

router = APIRouter(prefix="/plans", tags=["Plans & Habits"])

@router.get("/habits", response_model=BaseResponse[List[HabitResponse]])
async def list_habits(db: AsyncSession = Depends(get_db)):
    habits = await plan_svc.get_all_habits(db)
    return BaseResponse(success=True, data=habits)

@router.post("/habits", response_model=BaseResponse[HabitResponse])
async def create_habit(habit_data: HabitCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    habit = await plan_svc.create_habit(db, habit_data)
    return BaseResponse(success=True, data=habit, message="Habit created")

@router.get("/", response_model=BaseResponse[List[PlanResponse]])
async def list_public_plans(db: AsyncSession = Depends(get_db)):
    plans = await plan_svc.get_public_plans(db)
    return BaseResponse(success=True, data=plans)

@router.post("/", response_model=BaseResponse[PlanResponse])
async def create_plan(plan_data: PlanCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = await plan_svc.create_plan(db, plan_data, current_user)
    return BaseResponse(success=True, data=PlanResponse.model_validate(plan), message="Plan created")

@router.post("/select-plan", response_model=BaseResponse)
async def select_plan(request: SelectPlanRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_plan = await plan_svc.assign_plan_to_user(db, request, current_user)
    return BaseResponse(
        success=True, 
        message=f"Plan applied successfully. It will be active starting {user_plan.start_date}"
    )
