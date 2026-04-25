import pytest
import asyncio
from httpx import AsyncClient

# Add markers
pytestmark = pytest.mark.asyncio

async def create_user(client: AsyncClient, email: str = "audit@test.com") -> str:
    """Helper to create user and login"""
    payload = {
        "email": email,
        "password": "strongpassword123",
        "username": email.split("@")[0]
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    if resp.status_code == 400: # Already registered possibly
        pass
        
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "strongpassword123"})
    if login_resp.status_code == 200:
        return login_resp.json()["data"]["access_token"]
    return ""

async def test_api_discovery_health(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"

async def test_auth_validation(client: AsyncClient):
    # Missing fields
    resp = await client.post("/api/v1/auth/register", json={"email": "bad"})
    assert resp.status_code == 422
    
    # Successful
    resp = await client.post("/api/v1/auth/register", json={
        "email": "testauth@test.com",
        "password": "password",
        "username": "testauth"
    })
    assert resp.status_code == 201

async def test_habit_creation_and_plan_flow(client: AsyncClient):
    token = await create_user(client, "planflow@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create a habit
    h_payload = {
        "name": "Audit Habit 1",
        "description": "Desc",
        "category": "discipline",
        "difficulty": "medium",
        "base_score": 10
    }
    h_resp = await client.post("/api/v1/plans/habits", json=h_payload, headers=headers)
    assert h_resp.status_code == 200, h_resp.text
    habit_id = h_resp.json()["data"]["id"]
    
    # 2. List Habits
    h_list = await client.get("/api/v1/plans/habits")
    assert h_list.status_code == 200
    assert len(h_list.json()["data"]) >= 1
    
    # 3. Create a Plan
    p_payload = {
        "name": "Audit Plan",
        "is_public": True,
        "difficulty": "medium",
        "habits": [{"habit_id": habit_id}]
    }
    p_resp = await client.post("/api/v1/plans/", json=p_payload, headers=headers)
    print("Plan Resp:", p_resp.status_code, p_resp.text)
    assert p_resp.status_code == 200, p_resp.text
    plan_id = p_resp.json()["data"]["id"]
    
    # 4. Select the Plan
    s_resp = await client.post("/api/v1/plans/select-plan", json={"plan_id": plan_id}, headers=headers)
    assert s_resp.status_code == 200
    
    # 5. Check Today Execution (Should auto-initialize logs)
    t_resp = await client.get("/api/v1/execution/today", headers=headers)
    assert t_resp.status_code == 200
    logs = t_resp.json()["data"]
    assert len(logs) == 1
    log_habit_id = logs[0]["habit_id"]
    assert logs[0]["status"] == "pending"
    
    # 6. Complete Habit
    c_resp = await client.post("/api/v1/execution/habit/complete", json={"habit_id": log_habit_id, "note": "Done!"}, headers=headers)
    assert c_resp.status_code == 200
    assert c_resp.json()["data"]["status"] == "done"
    
    # 7. Check idempotency on complete (should fail if completed again)
    c_resp2 = await client.post("/api/v1/execution/habit/complete", json={"habit_id": log_habit_id}, headers=headers)
    assert c_resp2.status_code == 400
    
    # 8. Process Day (simulate end of day stats aggregation)
    pd_resp = await client.post("/api/v1/stats/process-day", headers=headers)
    assert pd_resp.status_code == 200
    
    # 9. Get Profile Stats
    prof_resp = await client.get("/api/v1/stats/profile", headers=headers)
    assert prof_resp.status_code == 200
    stats = prof_resp.json()["data"]
    assert stats["current_streak"] == 1
    assert stats["total_score"] > 0

async def test_concurrency_initialization(client: AsyncClient):
    token = await create_user(client, "concurrency@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup Habit/Plan
    h_resp = await client.post("/api/v1/plans/habits", json={"name": "C1", "category": "discipline", "difficulty": "medium", "base_score": 10}, headers=headers)
    assert h_resp.status_code == 200, h_resp.text
    p_resp = await client.post("/api/v1/plans/", json={"name": "CPlan", "is_public": False, "difficulty": "medium", "habits": [{"habit_id": h_resp.json()["data"]["id"]}]}, headers=headers)
    assert p_resp.status_code == 200
    await client.post("/api/v1/plans/select-plan", json={"plan_id": p_resp.json()["data"]["id"]}, headers=headers)
    
    # Fire 5 concurrent requests to /execution/today to attempt recreating logs simultaneously
    tasks = [client.get("/api/v1/execution/today", headers=headers) for _ in range(5)]
    results = await asyncio.gather(*tasks)
    
    # All should succeed
    for r in results:
        assert r.status_code == 200
        assert len(r.json()["data"]) == 1
