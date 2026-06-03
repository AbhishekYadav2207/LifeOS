import pytest
from httpx import AsyncClient
import datetime
from sqlalchemy import select
from app.models.log import DailyLog
from app.core.database import AsyncSessionLocal

@pytest.mark.asyncio
async def test_execution_lifecycle_and_rules(client: AsyncClient, mock_time):
    # Register and login user
    reg_resp = await client.post("/api/v1/auth/register", json={"email": "u1_exec@test.com", "password": "pass", "timezone": "America/New_York"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "u1_exec@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create habits: one with everyday config, one with weekends, one with weekdays config
    h1 = (await client.post("/api/v1/plans/habits", json={"name": "Everyday Habit", "category": "discipline", "difficulty": "easy", "base_score": 10}, headers=headers)).json()["data"]["id"]
    h2 = (await client.post("/api/v1/plans/habits", json={"name": "Weekday Habit", "category": "health", "difficulty": "medium", "base_score": 20}, headers=headers)).json()["data"]["id"]
    h3 = (await client.post("/api/v1/plans/habits", json={"name": "Weekend Habit", "category": "mind", "difficulty": "hard", "base_score": 30}, headers=headers)).json()["data"]["id"]
    
    # 2. Create Plan
    plan_resp = await client.post("/api/v1/plans/", json={
        "name": "Exec Plan",
        "difficulty": "medium",
        "habits": [
            {"habit_id": h1, "start_time": "08:00:00", "end_time": "12:00:00", "day_config": "everyday"},
            {"habit_id": h2, "start_time": "09:00:00", "end_time": "11:00:00", "day_config": "weekdays"},
            {"habit_id": h3, "start_time": "10:00:00", "end_time": "13:00:00", "day_config": "weekends"}
        ]
    }, headers=headers)
    p_id = plan_resp.json()["data"]["id"]
    
    # 3. Activate plan starting on 2026-06-01 (a Monday)
    mock_time.set_time(datetime.datetime(2026, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc))
    await client.post(f"/api/v1/plans/{p_id}/activate", headers=headers)
    
    # 4. Fetch today's execution on 2026-06-01 (Monday)
    # Expected: Everyday Habit and Weekday Habit are initialized. Weekend Habit is skipped.
    today_resp = await client.get("/api/v1/execution/today", headers=headers)
    assert today_resp.status_code == 200
    tasks = today_resp.json()["data"]
    assert len(tasks) == 2
    assert any(t["habit_id"] == h1 for t in tasks)
    assert any(t["habit_id"] == h2 for t in tasks)
    assert not any(t["habit_id"] == h3 for t in tasks)
    
    # 5. Complete Everyday Habit on time (current mock time is 09:00, end_time is 12:00)
    # Current timezone of user is America/New_York (UTC-4 or UTC-5).
    # Since mock_time is set to 2026-06-01 09:00:00 UTC, the local New York time is 05:00 AM.
    # 05:00 AM < 12:00 PM (end_time), so it is ON TIME.
    c1 = await client.post("/api/v1/execution/habit/complete", json={"habit_id": h1, "note": "On time!"}, headers=headers)
    assert c1.status_code == 200
    assert c1.json()["data"]["awarded_points"] == 10
    assert c1.json()["data"]["late_flag"] is False
    
    # Try to complete same habit again (should fail with 400 Already processed or invalid)
    c1_dup = await client.post("/api/v1/execution/habit/complete", json={"habit_id": h1}, headers=headers)
    assert c1_dup.status_code == 400
    
    # 6. Complete Weekday Habit late.
    # Shift time to 2026-06-01 17:00:00 UTC. Local time in NY is 13:00 PM.
    # end_time for h2 is 11:00 AM. 13:00 PM > 11:00 AM, so it is LATE.
    # Expected points: base_score // 2 = 20 // 2 = 10.
    mock_time.set_time(datetime.datetime(2026, 6, 1, 17, 0, 0, tzinfo=datetime.timezone.utc))
    c2 = await client.post("/api/v1/execution/habit/complete", json={"habit_id": h2, "note": "Late!"}, headers=headers)
    assert c2.status_code == 200
    assert c2.json()["data"]["awarded_points"] == 10
    assert c2.json()["data"]["late_flag"] is True
    
    # 7. Fetch weekends task on 2026-06-06 (Saturday)
    # Expected: Everyday Habit and Weekend Habit are initialized. Weekday Habit is skipped.
    mock_time.set_time(datetime.datetime(2026, 6, 6, 9, 0, 0, tzinfo=datetime.timezone.utc))
    today_weekend = await client.get("/api/v1/execution/today", headers=headers)
    tasks_w = today_weekend.json()["data"]
    assert len(tasks_w) == 2
    assert any(t["habit_id"] == h1 for t in tasks_w)
    assert any(t["habit_id"] == h3 for t in tasks_w)
    assert not any(t["habit_id"] == h2 for t in tasks_w)
