import pytest
from httpx import AsyncClient
import datetime
from sqlalchemy import select
from app.models.stat import UserStat
from app.core.database import AsyncSessionLocal

@pytest.mark.asyncio
async def test_stats_streaks_and_ranks(client: AsyncClient, mock_time):
    # Register and login user
    await client.post("/api/v1/auth/register", json={"email": "stats_user@test.com", "password": "pass", "timezone": "UTC"})
    l_resp = await client.post("/api/v1/auth/login", json={"email": "stats_user@test.com", "password": "pass"})
    token = l_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create habit and plan
    h1 = (await client.post("/api/v1/plans/habits", json={"name": "Stat Habit 1", "category": "focus", "difficulty": "easy", "base_score": 10}, headers=headers)).json()["data"]["id"]
    h2 = (await client.post("/api/v1/plans/habits", json={"name": "Stat Habit 2", "category": "health", "difficulty": "easy", "base_score": 20}, headers=headers)).json()["data"]["id"]
    
    plan_resp = await client.post("/api/v1/plans/", json={
        "name": "Stats Plan",
        "difficulty": "easy",
        "habits": [
            {"habit_id": h1, "start_time": "08:00:00", "end_time": "12:00:00", "day_config": "everyday"},
            {"habit_id": h2, "start_time": "08:00:00", "end_time": "12:00:00", "day_config": "everyday"}
        ]
    }, headers=headers)
    p_id = plan_resp.json()["data"]["id"]
    
    # 1. Day 1: 2026-06-01. Activate plan.
    mock_time.set_time(datetime.datetime(2026, 6, 1, 9, 0, 0, tzinfo=datetime.timezone.utc))
    await client.post(f"/api/v1/plans/{p_id}/activate", headers=headers)
    
    # Init logs for Day 1
    await client.get("/api/v1/execution/today", headers=headers)
    
    # Complete BOTH tasks (100% completion)
    await client.post("/api/v1/execution/habit/complete", json={"habit_id": h1}, headers=headers)
    await client.post("/api/v1/execution/habit/complete", json={"habit_id": h2}, headers=headers)
    
    # Process Day 1
    pd1 = await client.post("/api/v1/stats/process-day", headers=headers)
    assert pd1.status_code == 200
    assert pd1.json()["data"]["score_change"] == 30  # 10 + 20
    assert pd1.json()["data"]["streak"] == 1
    assert pd1.json()["data"]["rank"] == "Beginner" # < 50
    
    # Check profile
    prof1 = (await client.get("/api/v1/stats/profile", headers=headers)).json()["data"]
    assert prof1["total_points"] == 30
    assert prof1["current_streak"] == 1
    assert prof1["max_streak"] == 1
    
    # Try double process-day (idempotency check)
    pd1_dup = await client.post("/api/v1/stats/process-day", headers=headers)
    assert pd1_dup.status_code == 200
    assert pd1_dup.json()["data"]["status"] == "idempotent"
    
    # 2. Day 2: 2026-06-02.
    mock_time.set_time(datetime.datetime(2026, 6, 2, 9, 0, 0, tzinfo=datetime.timezone.utc))
    
    # Init logs for Day 2
    await client.get("/api/v1/execution/today", headers=headers)
    
    # Complete only Habit 1 (50% completion)
    # Habit 1: Done (+10 points)
    # Habit 2: Pending -> Missed (-10 points)
    # Expected day score change = 10 - 10 = 0.
    # Expected streak reset = 0.
    await client.post("/api/v1/execution/habit/complete", json={"habit_id": h1}, headers=headers)
    
    pd2 = await client.post("/api/v1/stats/process-day", headers=headers)
    print("pd2 response:", pd2.json())
    assert pd2.status_code == 200
    assert pd2.json()["data"]["score_change"] == 0
    assert pd2.json()["data"]["streak"] == 0
    
    prof2 = (await client.get("/api/v1/stats/profile", headers=headers)).json()["data"]
    assert prof2["total_points"] == 30
    assert prof2["current_streak"] == 0
    assert prof2["max_streak"] == 1 # max streak remains 1
    
    # 3. Day 3: 2026-06-03.
    mock_time.set_time(datetime.datetime(2026, 6, 3, 9, 0, 0, tzinfo=datetime.timezone.utc))
    
    # Init logs for Day 3
    await client.get("/api/v1/execution/today", headers=headers)
    
    # Complete NO tasks (0% completion)
    # Habit 1: Pending -> Missed (-5 points)
    # Habit 2: Pending -> Missed (-10 points)
    # Total score change = -15 points.
    pd3 = await client.post("/api/v1/stats/process-day", headers=headers)
    assert pd3.status_code == 200
    assert pd3.json()["data"]["score_change"] == -15
    
    prof3 = (await client.get("/api/v1/stats/profile", headers=headers)).json()["data"]
    assert prof3["total_points"] == 15 # 30 - 15 = 15
    assert prof3["current_streak"] == 0
    
    # 4. Day 4: 2026-06-04. Let's get rank up.
    mock_time.set_time(datetime.datetime(2026, 6, 4, 9, 0, 0, tzinfo=datetime.timezone.utc))
    # We will complete a high value habit to cross 50 points (Starter rank)
    h3 = (await client.post("/api/v1/plans/habits", json={"name": "Stat Habit 3", "category": "focus", "difficulty": "hard", "base_score": 60}, headers=headers)).json()["data"]["id"]
    
    p_id2 = (await client.post("/api/v1/plans/", json={
        "name": "Rank Up Plan", "difficulty": "hard", "habits": [{"habit_id": h3, "day_config": "everyday"}]
    }, headers=headers)).json()["data"]["id"]
    
    # Activate Rank Up Plan
    await client.post(f"/api/v1/plans/{p_id2}/activate", headers=headers)
    
    # Init logs for Day 4
    await client.get("/api/v1/execution/today", headers=headers)
    
    # Complete it
    await client.post("/api/v1/execution/habit/complete", json={"habit_id": h3}, headers=headers)
    
    # Process
    pd4 = await client.post("/api/v1/stats/process-day", headers=headers)
    print("pd4 response:", pd4.json())
    assert pd4.status_code == 200
    assert pd4.json()["data"]["score_change"] == 60
    assert pd4.json()["data"]["new_total"] == 75 # 15 + 60
    assert pd4.json()["data"]["rank"] == "Starter" # 75 is between 50 and 150
