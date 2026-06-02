import pytest
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch

# Add markers
pytestmark = pytest.mark.asyncio

async def create_user_with_plan(client: AsyncClient, email: str = "sim@test.com") -> tuple[str, str]:
    # 1. Register & Login
    await client.post("/api/v1/auth/register", json={"email": email, "password": "pass", "username": email.split("@")[0]})
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "pass"})
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Map habits
    h1 = await client.post("/api/v1/plans/habits", json={"name": "H1", "category": "discipline", "difficulty": "hard", "base_score": 10}, headers=headers)
    h2 = await client.post("/api/v1/plans/habits", json={"name": "H2", "category": "health", "difficulty": "hard", "base_score": 20}, headers=headers)
    h1_id = h1.json()["data"]["id"]
    h2_id = h2.json()["data"]["id"]
    
    # 3. Create Plan
    p_resp = await client.post("/api/v1/plans/", json={
        "name": "Sim Plan",
        "is_public": False,
        "difficulty": "medium",
        "habits": [{"habit_id": h1_id}, {"habit_id": h2_id}]
    }, headers=headers)
    plan_id = p_resp.json()["data"]["id"]
    
    # 4. Select Plan
    await client.post(f"/api/v1/plans/{plan_id}/activate", headers=headers)
    
    return token, headers

async def test_full_multi_day_simulation(client: AsyncClient):
    token, headers = await create_user_with_plan(client, "multi@test.com")
    
    base_time = datetime(2025, 1, 1, 10, 0, 0)
    
    # Helper to simulate an entire API day
    async def simulate_api_day(mock_time: datetime, completes_indices: list, mark_late: bool = False):
        with patch("app.services.execution_svc.get_current_time", return_value=mock_time), \
             patch("app.services.scoring_svc.get_current_time", return_value=mock_time):
             
             # 1. Init logs (fetch today execution)
             t_resp = await client.get("/api/v1/execution/today", headers=headers)
             assert t_resp.status_code == 200
             logs = t_resp.json()["data"]
             
             # 2. Complete chosen logs
             for idx in completes_indices:
                 log_id = logs[idx]["habit_id"]
                 # To accurately simulate late, we would normally configure the plan habit end time. 
                 # But we can also simulate it directly if "mark_late" requires a later time patch for the completion
                 completion_time = mock_time
                 if mark_late:
                     # Simulate late completion later in the day
                     completion_time = mock_time.replace(hour=23, minute=59)
                 
                 with patch("app.services.execution_svc.get_current_time", return_value=completion_time):
                     c_resp = await client.post("/api/v1/execution/habit/complete", json={"habit_id": log_id}, headers=headers)
                     assert c_resp.status_code == 200
             
             # 3. Aggregates day
             pd_resp = await client.post("/api/v1/stats/process-day", headers=headers)
             assert pd_resp.status_code == 200
             return pd_resp.json()["data"]
             
    # ===== Day 1: Full =====
    d1_time = base_time
    r1 = await simulate_api_day(d1_time, [0, 1])
    # Now check stats
    s1 = await client.get("/api/v1/stats/profile", headers=headers)
    s1_data = s1.json()["data"]
    assert s1_data["current_streak"] == 1
    
    # ===== Day 2: Partial (Only Habit H1) =====
    d2_time = base_time + timedelta(days=1)
    r2 = await simulate_api_day(d2_time, [0])
    s2 = await client.get("/api/v1/stats/profile", headers=headers)
    s2_data = s2.json()["data"]
    assert s2_data["current_streak"] == 0 # Reset due to partial
    
    # ===== Day 3: Missed =====
    d3_time = base_time + timedelta(days=2)
    r3 = await simulate_api_day(d3_time, [])
    s3 = await client.get("/api/v1/stats/profile", headers=headers)
    s3_data = s3.json()["data"]
    assert s3_data["current_streak"] == 0
    
    # ===== Day 4: Full (Returned) =====
    d4_time = base_time + timedelta(days=3)
    r4 = await simulate_api_day(d4_time, [0, 1])
    s4 = await client.get("/api/v1/stats/profile", headers=headers)
    s4_data = s4.json()["data"]
    assert s4_data["current_streak"] == 1 # Restarted
    
    # Final check on scores
    assert s4_data["total_score"] > 0
