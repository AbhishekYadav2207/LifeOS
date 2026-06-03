import pytest
from httpx import AsyncClient
import datetime
from sqlalchemy import select
from app.models.plan import UserPlan
from app.core.database import AsyncSessionLocal

@pytest.mark.asyncio
async def test_plan_activation_boundaries(client: AsyncClient, mock_time):
    # Register and login two users
    await client.post("/api/v1/auth/register", json={"email": "u1_act@test.com", "password": "pass", "timezone": "UTC"})
    await client.post("/api/v1/auth/register", json={"email": "u2_act@test.com", "password": "pass", "timezone": "UTC"})
    
    l1 = await client.post("/api/v1/auth/login", json={"email": "u1_act@test.com", "password": "pass"})
    l2 = await client.post("/api/v1/auth/login", json={"email": "u2_act@test.com", "password": "pass"})
    
    t1 = l1.json()["data"]["access_token"]
    t2 = l2.json()["data"]["access_token"]
    
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}
    
    # 1. User 1 creates a private habit
    h_resp = await client.post("/api/v1/plans/habits", json={
        "name": "Act Habit", "category": "health", "difficulty": "easy", "base_score": 10, "is_public": False
    }, headers=h1)
    habit_id = h_resp.json()["data"]["id"]
    
    # 2. User 1 creates Plan A (Private) and Plan B (Private)
    pA = await client.post("/api/v1/plans/", json={
        "name": "Plan A", "difficulty": "easy", "is_public": False, "habits": [{"habit_id": habit_id}]
    }, headers=h1)
    pA_id = pA.json()["data"]["id"]
    
    pB = await client.post("/api/v1/plans/", json={
        "name": "Plan B", "difficulty": "easy", "is_public": False, "habits": [{"habit_id": habit_id}]
    }, headers=h1)
    pB_id = pB.json()["data"]["id"]
    
    # 3. User 2 tries to activate User 1's private Plan A (should fail with 403)
    act_fail = await client.post(f"/api/v1/plans/{pA_id}/activate", headers=h2)
    assert act_fail.status_code == 403
    
    # 4. User 1 activates Plan A (should succeed)
    # Set mock date to 2026-06-01
    mock_time.set_time(datetime.datetime(2026, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc))
    act_ok1 = await client.post(f"/api/v1/plans/{pA_id}/activate", headers=h1)
    assert act_ok1.status_code == 200
    
    # Verify in DB
    async with AsyncSessionLocal() as session:
        up_q = select(UserPlan).where(UserPlan.user_id == l1.json()["data"]["user_id"], UserPlan.active == True)
        active_plans = (await session.execute(up_q)).scalars().all()
        assert len(active_plans) == 1
        assert active_plans[0].plan_id == pA_id
        assert active_plans[0].start_date == datetime.date(2026, 6, 1)
        assert active_plans[0].end_date is None
        
    # 5. User 1 activates Plan B on 2026-06-03 (plan switch)
    mock_time.set_time(datetime.datetime(2026, 6, 3, 9, 0, 0, tzinfo=datetime.timezone.utc))
    act_ok2 = await client.post(f"/api/v1/plans/{pB_id}/activate", headers=h1)
    assert act_ok2.status_code == 200
    
    # Verify in DB: Plan A is now inactive and has end_date = 2026-06-03
    async with AsyncSessionLocal() as session:
        # Check active plan is Plan B
        up_active_q = select(UserPlan).where(UserPlan.user_id == l1.json()["data"]["user_id"], UserPlan.active == True)
        active_plan = (await session.execute(up_active_q)).scalars().first()
        assert active_plan is not None
        assert active_plan.plan_id == pB_id
        assert active_plan.start_date == datetime.date(2026, 6, 3)
        
        # Check inactive Plan A
        up_inactive_q = select(UserPlan).where(UserPlan.user_id == l1.json()["data"]["user_id"], UserPlan.plan_id == pA_id)
        old_plan = (await session.execute(up_inactive_q)).scalars().first()
        assert old_plan is not None
        assert old_plan.active is False
        assert old_plan.end_date == datetime.date(2026, 6, 3)
