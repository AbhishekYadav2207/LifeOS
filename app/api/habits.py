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
    description="Returns all public habits and habits created by the current user.",
)
async def list_habits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Habit).where((Habit.is_public == True) | (Habit.created_by == current_user.id))
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


# ---------------------------------------------------------------------------
# Habit Dependencies Endpoints
# ---------------------------------------------------------------------------

from app.models.habit import HabitDependency
from app.schemas.habit import HabitDependencyCreate, HabitDependencyResponse
from fastapi import HTTPException

@router.post(
    "/dependencies",
    response_model=BaseResponse[HabitDependencyResponse],
    summary="Create a habit dependency link",
)
async def create_habit_dependency(
    dep_data: HabitDependencyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify both habits exist and belong to the user (or are public)
    h_query = select(Habit).where(
        Habit.id.in_([dep_data.parent_habit_id, dep_data.child_habit_id]),
        (Habit.is_public == True) | (Habit.created_by == current_user.id)
    )
    res = await db.execute(h_query)
    habits = res.scalars().all()
    if len(habits) < 2 and dep_data.parent_habit_id != dep_data.child_habit_id:
        raise HTTPException(status_code=404, detail="Parent or child habit not found or inaccessible")

    # Check for self-loop
    if dep_data.parent_habit_id == dep_data.child_habit_id:
        raise HTTPException(status_code=400, detail="Cyclic dependencies are not allowed (self-loop detected)")

    # Check for existing dependency link to prevent duplicates
    existing_q = select(HabitDependency).where(
        HabitDependency.user_id == current_user.id,
        HabitDependency.parent_habit_id == dep_data.parent_habit_id,
        HabitDependency.child_habit_id == dep_data.child_habit_id
    )
    existing_link = (await db.execute(existing_q)).scalars().first()
    if existing_link:
        raise HTTPException(status_code=400, detail="This dependency link already exists")

    # DFS Cycle Detection check
    # Get all dependencies for the user
    stmt = select(HabitDependency).where(HabitDependency.user_id == current_user.id)
    res_deps = await db.execute(stmt)
    deps = res_deps.scalars().all()
    
    # Build graph
    graph = {}
    for d in deps:
        if d.parent_habit_id not in graph:
            graph[d.parent_habit_id] = []
        graph[d.parent_habit_id].append(d.child_habit_id)
        
    # Add proposed dependency
    if dep_data.parent_habit_id not in graph:
        graph[dep_data.parent_habit_id] = []
    graph[dep_data.parent_habit_id].append(dep_data.child_habit_id)
    
    # DFS cycle detection
    visited = set()
    rec_stack = set()
    
    def dfs(node: int) -> bool:
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
                
        rec_stack.remove(node)
        return False
        
    # Check cycle starting from any node in graph
    has_cycle = False
    for node in graph:
        if node not in visited:
            if dfs(node):
                has_cycle = True
                break
                
    if has_cycle:
        raise HTTPException(status_code=400, detail="Cyclic dependencies are not allowed")

    # Create dependency
    new_dep = HabitDependency(
        user_id=current_user.id,
        parent_habit_id=dep_data.parent_habit_id,
        child_habit_id=dep_data.child_habit_id,
        chain_order=dep_data.chain_order
    )
    db.add(new_dep)
    try:
        await db.commit()
        await db.refresh(new_dep)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save dependency: {str(e)}")

    return BaseResponse(success=True, data=new_dep, message="Dependency link created successfully")


@router.get(
    "/dependencies",
    response_model=BaseResponse[List[HabitDependencyResponse]],
    summary="List all habit dependency links for user",
)
async def list_habit_dependencies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HabitDependency).where(HabitDependency.user_id == current_user.id)
    res = await db.execute(stmt)
    deps = res.scalars().all()
    return BaseResponse(success=True, data=deps)


@router.delete(
    "/dependencies/{parent_id}/{child_id}",
    response_model=BaseResponse,
    summary="Delete a habit dependency link",
)
async def delete_habit_dependency(
    parent_id: int,
    child_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HabitDependency).where(
        HabitDependency.user_id == current_user.id,
        HabitDependency.parent_habit_id == parent_id,
        HabitDependency.child_habit_id == child_id
    )
    res = await db.execute(stmt)
    dep = res.scalars().first()
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency link not found")
        
    await db.delete(dep)
    await db.commit()
    return BaseResponse(success=True, message="Dependency link deleted successfully")
