import pytest
from datetime import datetime, date, time
from unittest.mock import patch
from app.models.enums import HabitCategory
from app.models.plan import UserPlan, PlanHabit
from app.models.stat import UserStat
from sqlalchemy.future import select
from tests.utils import create_test_user, create_test_habit, create_test_plan

pytestmark = pytest.mark.asyncio

async def test_create_public_plan_with_private_habit_fails(client, db_session):
    # Register & login
    user = await create_test_user(db_session, email="owner@test.com")
    response = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    token = response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a private habit
    h_res = await client.post(
        "/api/v1/plans/habits",
        json={"name": "Private Habit", "category": "mind", "difficulty": "easy", "base_score": 10, "is_public": False},
        headers=headers
    )
    assert h_res.status_code == 200
    habit_id = h_res.json()["data"]["id"]

    # Try creating a public plan with this private habit
    plan_payload = {
        "name": "Public Plan with Private Habit",
        "is_public": True,
        "difficulty": "medium",
        "habits": [{"habit_id": habit_id}]
    }
    plan_res = await client.post("/api/v1/plans/", json=plan_payload, headers=headers)
    assert plan_res.status_code == 400
    assert "Cannot include private habits in a public plan" in plan_res.json()["detail"]


async def test_private_plan_habits_security_check(client, db_session):
    # User A creates a private plan
    user_a = await create_test_user(db_session, email="user_a@test.com")
    habit_a = await create_test_habit(db_session, name="Private Habit A", creator_id=user_a.id)
    habit_a.is_public = False
    await db_session.commit()
    
    plan_a = await create_test_plan(db_session, creator_id=user_a.id, habits=[{"habit": habit_a}])
    
    # Manually make the plan private
    plan_a.is_public = False
    await db_session.commit()

    # User B logs in
    user_b = await create_test_user(db_session, email="user_b@test.com")
    response = await client.post("/api/v1/auth/login", json={"email": user_b.email, "password": "password"})
    token = response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # User B tries to view User A's private plan habits
    res = await client.get(f"/api/v1/plans/{plan_a.id}/habits", headers=headers)
    assert res.status_code == 403
    assert "Cannot view habits of a private plan you do not own" in res.json()["detail"]


async def test_scoring_floored_at_zero(client, db_session):
    # Create user & plan
    user = await create_test_user(db_session, email="stats@test.com")
    habit = await create_test_habit(db_session, name="H1", category=HabitCategory.focus, base_score=50)
    plan = await create_test_plan(db_session, creator_id=user.id, habits=[{"habit": habit}])
    
    up = UserPlan(user_id=user.id, plan_id=plan.id, active=True, start_date=datetime.utcnow().date())
    db_session.add(up)
    await db_session.commit()

    response = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    token = response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Initialize logs for today (all pending)
    await client.get("/api/v1/execution/today", headers=headers)

    # Process day with the pending habit (sets to missed, which gives negative score change)
    process_res = await client.post("/api/v1/stats/process-day", headers=headers)
    assert process_res.status_code == 200
    pdata = process_res.json()["data"]
    
    # Assert score_change is negative (-25), but new_total is floored at 0
    assert pdata["score_change"] == -25
    assert pdata["new_total"] == 0

    # Retrieve profile to verify all points are floored at 0
    profile_res = await client.get("/api/v1/stats/profile", headers=headers)
    assert profile_res.status_code == 200
    prof_data = profile_res.json()["data"]
    assert prof_data["total_score"] == 0
    assert prof_data["focus_points"] == 0


async def test_day_config_scheduling(client, db_session):
    user = await create_test_user(db_session, email="sched@test.com")
    h_wkday = await create_test_habit(db_session, name="Weekday Habit", category=HabitCategory.discipline)
    h_wkend = await create_test_habit(db_session, name="Weekend Habit", category=HabitCategory.health)
    
    plan = await create_test_plan(db_session, creator_id=user.id)
    
    # Add custom plan habits
    ph1 = PlanHabit(plan_id=plan.id, habit_id=h_wkday.id, day_config="weekdays", start_time=time(8,0), end_time=time(20,0))
    ph2 = PlanHabit(plan_id=plan.id, habit_id=h_wkend.id, day_config="weekends", start_time=time(8,0), end_time=time(20,0))
    db_session.add_all([ph1, ph2])
    
    up = UserPlan(user_id=user.id, plan_id=plan.id, active=True, start_date=datetime.utcnow().date())
    db_session.add(up)
    await db_session.commit()

    response = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    token = response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate Saturday (weekend = Saturday = weekday 5)
    saturday = datetime(2026, 6, 6, 12, 0, 0) # Saturday
    with patch("app.services.execution_svc.get_current_time", return_value=saturday):
        t_resp = await client.get("/api/v1/execution/today", headers=headers)
        assert t_resp.status_code == 200
        logs = t_resp.json()["data"]
        # Only the weekend habit should be generated
        assert len(logs) == 1
        assert logs[0]["name"] == "Weekend Habit"

    # Simulate Monday (weekday = Monday = weekday 0)
    # Rollback session logs to allow re-initialization
    await db_session.execute(select(UserStat)) # Clear session state query
    # Clear logs created for saturday to test clean monday initialization
    from app.models.log import DailyLog
    # We can just clean DB daily logs first
    logs_q = await db_session.execute(select(DailyLog).where(DailyLog.user_id == user.id))
    for log in logs_q.scalars().all():
        await db_session.delete(log)
    await db_session.commit()

    monday = datetime(2026, 6, 8, 12, 0, 0) # Monday
    with patch("app.services.execution_svc.get_current_time", return_value=monday):
        t_resp = await client.get("/api/v1/execution/today", headers=headers)
        assert t_resp.status_code == 200
        logs = t_resp.json()["data"]
        # Only the weekday habit should be generated
        assert len(logs) == 1
        assert logs[0]["name"] == "Weekday Habit"
