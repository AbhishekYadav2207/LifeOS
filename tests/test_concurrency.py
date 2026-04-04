import pytest
import asyncio
from datetime import datetime, date
from app.models.enums import HabitCategory
from app.models.plan import UserPlan
from tests.utils import create_test_user, create_test_habit, create_test_plan
from app.services.execution_svc import mark_habit_completed

@pytest.mark.asyncio
async def test_concurrent_execution(client, db_session):
    user = await create_test_user(db_session, email="concurrent@test.com")
    habit = await create_test_habit(db_session, category=HabitCategory.discipline)
    plan = await create_test_plan(db_session, creator_id=user.id, habits=[{"habit": habit}])
    up = UserPlan(user_id=user.id, plan_id=plan.id, active=True, start_date=datetime.utcnow().date())
    db_session.add(up)
    await db_session.commit()
    
    resp = await client.post("/api/v1/auth/login", json={"email": "concurrent@test.com", "password": "password"})
    headers = {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}
    
    # 1. Initialize
    await client.get("/api/v1/execution/today", headers=headers)
    
    # 2. Fire identical completions simultaneously
    task1 = client.post("/api/v1/execution/habit/complete", json={"habit_id": habit.id}, headers=headers)
    task2 = client.post("/api/v1/execution/habit/complete", json={"habit_id": habit.id}, headers=headers)
    task3 = client.post("/api/v1/execution/habit/complete", json={"habit_id": habit.id}, headers=headers)
    
    responses = await asyncio.gather(task1, task2, task3)
    
    # Assert exactly 1 succeeds (status 200), and the rest fail gracefully with 400 'already processed'
    status_codes = [r.status_code for r in responses]
    assert status_codes.count(200) == 1
    assert status_codes.count(400) == 2
