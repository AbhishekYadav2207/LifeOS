import pytest
import asyncio
import datetime
from httpx import AsyncClient
from sqlalchemy import select
from app.models.plan import UserPlan
from app.models.log import DailyLog
from app.models.habit import Habit
from app.core.database import AsyncSessionLocal

@pytest.mark.asyncio
async def test_habit_completion_race(client: AsyncClient, mock_time):
    # Register and login user
    reg_resp = await client.post("/api/v1/auth/register", json={"email": "race_user@test.com", "password": "pass", "timezone": "UTC"})
    u_id = reg_resp.json()["data"]["id"]
    l_resp = await client.post("/api/v1/auth/login", json={"email": "race_user@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create habit
    h_resp = await client.post("/api/v1/plans/habits", json={"name": "Race Habit", "category": "focus", "difficulty": "easy", "base_score": 10}, headers=headers)
    h_id = h_resp.json()["data"]["id"]
    
    # Create plan
    p_resp = await client.post("/api/v1/plans/", json={
        "name": "Race Plan", "difficulty": "easy", "habits": [{"habit_id": h_id}]
    }, headers=headers)
    p_id = p_resp.json()["data"]["id"]
    
    # Activate plan
    mock_time.set_time(datetime.datetime(2026, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc))
    await client.post(f"/api/v1/plans/{p_id}/activate", headers=headers)
    
    # Initialize log
    await client.get("/api/v1/execution/today", headers=headers)
    
    # Fire 50 concurrent habit completion requests
    tasks = [
        client.post("/api/v1/execution/habit/complete", json={"habit_id": h_id, "note": f"Race {i}"}, headers=headers)
        for i in range(50)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions from results if any
    valid_results = [r for r in results if not isinstance(r, Exception)]
    
    # Exactly one request must succeed (HTTP 200)
    # The rest must fail (HTTP 400 Bad Request)
    success_count = sum(1 for r in valid_results if r.status_code == 200)
    fail_count = sum(1 for r in valid_results if r.status_code == 400)
    
    assert success_count == 1
    assert fail_count + (len(results) - len(valid_results)) == 49
    
    # Verify DB state: log status is "done", awarded_points is 10
    async with AsyncSessionLocal() as session:
        log_q = select(DailyLog).where(DailyLog.user_id == u_id, DailyLog.habit_id == h_id)
        log = (await session.execute(log_q)).scalars().first()
        assert log is not None
        assert log.status == "done"
        assert log.awarded_points == 10

@pytest.mark.asyncio
async def test_plan_activation_race(client: AsyncClient, mock_time):
    # Register and login user
    reg_resp = await client.post("/api/v1/auth/register", json={"email": "plan_race_user@test.com", "password": "pass", "timezone": "UTC"})
    u_id = reg_resp.json()["data"]["id"]
    l_resp = await client.post("/api/v1/auth/login", json={"email": "plan_race_user@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create two plans
    p1 = (await client.post("/api/v1/plans/", json={"name": "Plan 1", "difficulty": "easy", "habits": []}, headers=headers)).json()["data"]["id"]
    p2 = (await client.post("/api/v1/plans/", json={"name": "Plan 2", "difficulty": "easy", "habits": []}, headers=headers)).json()["data"]["id"]
    
    mock_time.set_time(datetime.datetime(2026, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc))
    
    # Fire 50 concurrent activation requests (25 for Plan 1, 25 for Plan 2)
    tasks = []
    for i in range(25):
        tasks.append(client.post(f"/api/v1/plans/{p1}/activate", headers=headers))
        tasks.append(client.post(f"/api/v1/plans/{p2}/activate", headers=headers))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify DB state: Exactly one active plan must exist for this user in the end
    async with AsyncSessionLocal() as session:
        up_q = select(UserPlan).where(UserPlan.user_id == u_id, UserPlan.active == True)
        active_plans = (await session.execute(up_q)).scalars().all()
        assert len(active_plans) == 1

@pytest.mark.asyncio
async def test_duplicate_habit_creation_race(client: AsyncClient):
    # Register and login user
    await client.post("/api/v1/auth/register", json={"email": "habit_race_user@test.com", "password": "pass", "timezone": "UTC"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "habit_race_user@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Fire 50 concurrent requests to create a habit with the same name
    tasks = [
        client.post("/api/v1/plans/habits", json={
            "name": "Same Name Habit", "category": "focus", "difficulty": "easy", "base_score": 10
        }, headers=headers)
        for i in range(50)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify DB has exactly one habit with this name
    async with AsyncSessionLocal() as session:
        h_q = select(Habit).where(Habit.name == "Same Name Habit")
        habits = (await session.execute(h_q)).scalars().all()
        assert len(habits) == 1
