import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_habit_crud_and_ownership(client: AsyncClient):
    # Register two users
    u1_resp = await client.post("/api/v1/auth/register", json={"email": "u1_habits@test.com", "password": "pass", "timezone": "UTC"})
    u2_resp = await client.post("/api/v1/auth/register", json={"email": "u2_habits@test.com", "password": "pass", "timezone": "UTC"})
    
    u1_login = await client.post("/api/v1/auth/login", json={"email": "u1_habits@test.com", "password": "pass"})
    u2_login = await client.post("/api/v1/auth/login", json={"email": "u2_habits@test.com", "password": "pass"})
    
    u1_token = u1_login.json()["data"]["access_token"]
    u2_token = u2_login.json()["data"]["access_token"]
    
    h1_headers = {"Authorization": f"Bearer {u1_token}"}
    h2_headers = {"Authorization": f"Bearer {u2_token}"}
    
    # 1. Create habit as User 1 (Private)
    create_resp = await client.post("/api/v1/plans/habits", json={
        "name": "User 1 Habit",
        "category": "discipline",
        "difficulty": "medium",
        "base_score": 10,
        "is_public": False
    }, headers=h1_headers)
    assert create_resp.status_code == 200
    h1_id = create_resp.json()["data"]["id"]
    
    # 2. List habits for User 1 (should see h1)
    list_resp = await client.get("/api/v1/plans/habits", headers=h1_headers)
    assert len(list_resp.json()["data"]) >= 1
    assert any(h["id"] == h1_id for h in list_resp.json()["data"])
    
    # 3. List habits for User 2 (should not see h1 because it's private)
    list2_resp = await client.get("/api/v1/plans/habits", headers=h2_headers)
    assert not any(h["id"] == h1_id for h in list2_resp.json()["data"])
    
    # 4. User 2 tries to update User 1's habit (should fail with 403)
    update_resp = await client.put(f"/api/v1/plans/habits/{h1_id}", json={
        "name": "Hacked Habit",
        "category": "focus",
        "difficulty": "hard",
        "base_score": 20,
        "is_public": False
    }, headers=h2_headers)
    assert update_resp.status_code == 403
    
    # 5. User 1 updates own habit (should succeed)
    update_ok = await client.put(f"/api/v1/plans/habits/{h1_id}", json={
        "name": "User 1 Updated Habit",
        "category": "focus",
        "difficulty": "hard",
        "base_score": 20,
        "is_public": True  # Change to public
    }, headers=h1_headers)
    assert update_ok.status_code == 200
    assert update_ok.json()["data"]["name"] == "User 1 Updated Habit"
    assert update_ok.json()["data"]["is_public"] is True
    
    # 6. User 2 lists habits again (now should see it because it is public!)
    list3_resp = await client.get("/api/v1/plans/habits", headers=h2_headers)
    assert any(h["id"] == h1_id for h in list3_resp.json()["data"])
    
    # 7. User 2 tries to delete it (should fail with 403)
    del_fail = await client.delete(f"/api/v1/plans/habits/{h1_id}", headers=h2_headers)
    assert del_fail.status_code == 403
    
    # 8. User 1 deletes own habit (should succeed)
    del_ok = await client.delete(f"/api/v1/plans/habits/{h1_id}", headers=h1_headers)
    assert del_ok.status_code == 200
    
    # 9. Verify deleted
    list4_resp = await client.get("/api/v1/plans/habits", headers=h1_headers)
    assert not any(h["id"] == h1_id for h in list4_resp.json()["data"])
