import pytest
from datetime import time, timedelta, datetime
from app.models.enums import HabitCategory
from app.models.plan import UserPlan
from tests.utils import create_test_user, create_test_habit, create_test_plan

@pytest.mark.asyncio
async def test_execution_no_habits(client, db_session):
    user = await create_test_user(db_session, email="exec1@test.com")
    resp = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    res = await client.get("/api/v1/execution/today", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["data"]) == 0 # no assigned plan

@pytest.mark.asyncio
async def test_today_habit_generation(client, db_session):
    user = await create_test_user(db_session, email="exec2@test.com")
    habit = await create_test_habit(db_session, category=HabitCategory.discipline)
    plan = await create_test_plan(db_session, creator_id=user.id, habits=[{"habit": habit}])
    
    # Force active user plan starting TODAY (usually it starts next day via API)
    up = UserPlan(user_id=user.id, plan_id=plan.id, active=True, start_date=datetime.utcnow().date())
    db_session.add(up)
    await db_session.commit()
    
    resp = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    res = await client.get("/api/v1/execution/today", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["status"] == "pending"

@pytest.mark.asyncio
async def test_habit_completion_and_duplicates(client, db_session):
    user = await create_test_user(db_session, email="exec3@test.com")
    habit = await create_test_habit(db_session)
    plan = await create_test_plan(db_session, creator_id=user.id, habits=[{"habit": habit}])
    up = UserPlan(user_id=user.id, plan_id=plan.id, active=True, start_date=datetime.utcnow().date())
    db_session.add(up)
    await db_session.commit()
    
    resp = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    headers = {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}
    
    # Initialize logs
    await client.get("/api/v1/execution/today", headers=headers)
    
    # Compete successfully
    res = await client.post("/api/v1/execution/habit/complete", json={"habit_id": habit.id}, headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "done"
    
    # Complete again (idempotency block)
    res2 = await client.post("/api/v1/execution/habit/complete", json={"habit_id": habit.id}, headers=headers)
    assert res2.status_code == 400
    assert "already processed" in res2.json()["detail"].lower()
