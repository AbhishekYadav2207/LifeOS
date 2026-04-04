import pytest
from datetime import datetime, date, timedelta, time
from app.models.enums import HabitCategory
from app.models.plan import UserPlan
from app.models.log import DailyLog
from app.models.stat import UserStat
from sqlalchemy.future import select
from tests.utils import create_test_user, create_test_habit, create_test_plan

@pytest.mark.asyncio
async def test_scoring_matrix_all_ontime(client, db_session):
    user = await create_test_user(db_session, email="score1@test.com")
    habit1 = await create_test_habit(db_session, name="H1", category=HabitCategory.focus, base_score=20)
    habit2 = await create_test_habit(db_session, name="H2", category=HabitCategory.health, base_score=10)
    
    plan = await create_test_plan(db_session, creator_id=user.id, habits=[{"habit": habit1}, {"habit": habit2}])
    up = UserPlan(user_id=user.id, plan_id=plan.id, active=True, start_date=datetime.utcnow().date())
    db_session.add(up)
    await db_session.commit()
    
    resp = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    headers = {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}
    
    # Init and mark done ON TIME
    await client.get("/api/v1/execution/today", headers=headers)
    await client.post("/api/v1/execution/habit/complete", json={"habit_id": habit1.id}, headers=headers)
    await client.post("/api/v1/execution/habit/complete", json={"habit_id": habit2.id}, headers=headers)
    
    # Process
    process = await client.post("/api/v1/stats/process-day", headers=headers)
    assert process.status_code == 200
    pdata = process.json()["data"]
    assert pdata["score_change"] == 30 # Full 20 + 10
    assert pdata["streak"] == 1
    
    # Check Profile
    prof = await client.get("/api/v1/stats/profile", headers=headers)
    data = prof.json()["data"]
    assert data["focus_points"] == 20
    assert data["health_points"] == 10
    assert data["total_points"] == 30

@pytest.mark.asyncio
async def test_scoring_matrix_some_missed(client, db_session):
    user = await create_test_user(db_session, email="score2@test.com")
    habit1 = await create_test_habit(db_session, name="H3", category=HabitCategory.focus, base_score=20)
    habit2 = await create_test_habit(db_session, name="H4", category=HabitCategory.mind, base_score=10)
    
    plan = await create_test_plan(db_session, creator_id=user.id, habits=[{"habit": habit1}, {"habit": habit2}])
    up = UserPlan(user_id=user.id, plan_id=plan.id, active=True, start_date=datetime.utcnow().date())
    
    # Pre-set streak
    ust = await db_session.execute(select(UserStat).where(UserStat.user_id==user.id))
    stat = ust.scalars().first()
    stat.current_streak = 5
    stat.max_streak = 5
    
    db_session.add(up)
    await db_session.commit()
    
    resp = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    headers = {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}
    
    # Init logs but only complete 1
    await client.get("/api/v1/execution/today", headers=headers)
    await client.post("/api/v1/execution/habit/complete", json={"habit_id": habit1.id}, headers=headers)
    
    # Process
    process = await client.post("/api/v1/stats/process-day", headers=headers)
    pdata = process.json()["data"]
    
    # H1 = +20, H2_Missed = -5 (50% penalty of 10) => +15
    assert pdata["score_change"] == 15
    assert pdata["streak"] == 0 # Streak reset!
    
    # process twice idempotency check
    process2 = await client.post("/api/v1/stats/process-day", headers=headers)
    assert process2.json()["data"]["status"] == "idempotent"
    assert process2.json()["data"]["score_change"] == 0
