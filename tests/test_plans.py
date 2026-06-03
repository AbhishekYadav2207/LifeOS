import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_plan_crud_and_validation(client: AsyncClient):
    # Register and login user
    await client.post("/api/v1/auth/register", json={"email": "u1_plans@test.com", "password": "pass", "timezone": "UTC"})
    u1_login = await client.post("/api/v1/auth/login", json={"email": "u1_plans@test.com", "password": "pass"})
    u1_token = u1_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {u1_token}"}
    
    # 1. Create a public habit and a private habit
    h_pub_resp = await client.post("/api/v1/plans/habits", json={
        "name": "Public Plan Habit", "category": "discipline", "difficulty": "easy", "base_score": 10, "is_public": True
    }, headers=headers)
    h_pub_id = h_pub_resp.json()["data"]["id"]
    
    h_priv_resp = await client.post("/api/v1/plans/habits", json={
        "name": "Private Plan Habit", "category": "focus", "difficulty": "medium", "base_score": 15, "is_public": False
    }, headers=headers)
    h_priv_id = h_priv_resp.json()["data"]["id"]
    
    # 2. Try to create a public plan containing a private habit (should fail with 400 Bad Request)
    bad_plan = await client.post("/api/v1/plans/", json={
        "name": "Invalid Public Plan",
        "difficulty": "medium",
        "is_public": True,
        "habits": [{"habit_id": h_priv_id, "start_time": "08:00:00", "end_time": "10:00:00"}]
    }, headers=headers)
    assert bad_plan.status_code == 400
    assert "private" in bad_plan.json()["detail"].lower()
    
    # 3. Create a valid public plan containing public habit
    plan_resp = await client.post("/api/v1/plans/", json={
        "name": "Valid Public Plan",
        "difficulty": "easy",
        "is_public": True,
        "habits": [{"habit_id": h_pub_id, "start_time": "09:00:00", "end_time": "11:00:00"}]
    }, headers=headers)
    assert plan_resp.status_code == 200
    p_id = plan_resp.json()["data"]["id"]
    
    # 4. Get habits for plan
    plan_habits_resp = await client.get(f"/api/v1/plans/{p_id}/habits", headers=headers)
    assert plan_habits_resp.status_code == 200
    assert len(plan_habits_resp.json()["data"]) == 1
    assert plan_habits_resp.json()["data"][0]["id"] == h_pub_id
    assert plan_habits_resp.json()["data"][0]["start_time"] == "09:00:00"
    
    # 5. List public plans (should see it)
    list_pub = await client.get("/api/v1/plans/")
    assert len(list_pub.json()["data"]) >= 1
    assert any(p["id"] == p_id for p in list_pub.json()["data"])
    
    # 6. Update plan: add a private habit (must switch to private plan)
    upd_resp = await client.put(f"/api/v1/plans/{p_id}", json={
        "name": "Now Private Plan",
        "difficulty": "medium",
        "is_public": False,
        "habits": [
            {"habit_id": h_pub_id, "start_time": "09:00:00", "end_time": "11:00:00"},
            {"habit_id": h_priv_id, "start_time": "12:00:00", "end_time": "14:00:00"}
        ]
    }, headers=headers)
    assert upd_resp.status_code == 200
    assert upd_resp.json()["data"]["is_public"] is False
    
    # 7. Delete plan
    del_resp = await client.delete(f"/api/v1/plans/{p_id}", headers=headers)
    assert del_resp.status_code == 200
