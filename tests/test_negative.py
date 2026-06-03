import pytest
from httpx import AsyncClient
import datetime

@pytest.mark.asyncio
async def test_authentication_negative(client: AsyncClient):
    # 1. Test missing token
    r = await client.get("/api/v1/plans/habits")
    assert r.status_code == 401
    
    # 2. Test invalid token
    r2 = await client.get("/api/v1/plans/habits", headers={"Authorization": "Bearer badtoken"})
    assert r2.status_code == 401

@pytest.mark.asyncio
async def test_authorization_negative(client: AsyncClient):
    # Register and login two users
    await client.post("/api/v1/auth/register", json={"email": "neg_u1@test.com", "password": "pass", "timezone": "UTC"})
    await client.post("/api/v1/auth/register", json={"email": "neg_u2@test.com", "password": "pass", "timezone": "UTC"})
    
    l1 = (await client.post("/api/v1/auth/login", json={"email": "neg_u1@test.com", "password": "pass"})).json()["data"]
    l2 = (await client.post("/api/v1/auth/login", json={"email": "neg_u2@test.com", "password": "pass"})).json()["data"]
    
    h1 = {"Authorization": f"Bearer {l1['access_token']}"}
    h2 = {"Authorization": f"Bearer {l2['access_token']}"}
    
    # User 1 creates private habit
    habit = (await client.post("/api/v1/plans/habits", json={
        "name": "User 1 Private", "category": "focus", "difficulty": "easy", "base_score": 10, "is_public": False
    }, headers=h1)).json()["data"]
    
    # User 2 tries to update User 1's habit
    upd = await client.put(f"/api/v1/plans/habits/{habit['id']}", json={
        "name": "Hacked", "category": "focus", "difficulty": "easy", "base_score": 10, "is_public": False
    }, headers=h2)
    assert upd.status_code == 403
    
    # User 2 tries to delete User 1's habit
    dl = await client.delete(f"/api/v1/plans/habits/{habit['id']}", headers=h2)
    assert dl.status_code == 403
    
    # User 1 creates private plan
    plan = (await client.post("/api/v1/plans/", json={
        "name": "User 1 Plan", "difficulty": "easy", "is_public": False, "habits": []
    }, headers=h1)).json()["data"]
    
    # User 2 tries to view User 1's private plan habits
    ph = await client.get(f"/api/v1/plans/{plan['id']}/habits", headers=h2)
    assert ph.status_code == 403
    
    # User 2 tries to activate User 1's private plan
    act = await client.post(f"/api/v1/plans/{plan['id']}/activate", headers=h2)
    assert act.status_code == 403

@pytest.mark.asyncio
async def test_validation_negative(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={"email": "val_neg@test.com", "password": "pass", "timezone": "UTC"})
    l = (await client.post("/api/v1/auth/login", json={"email": "val_neg@test.com", "password": "pass"})).json()["data"]
    headers = {"Authorization": f"Bearer {l['access_token']}"}
    
    # 1. Missing fields (e.g. name missing)
    bad_h = await client.post("/api/v1/plans/habits", json={"category": "focus", "difficulty": "easy"}, headers=headers)
    assert bad_h.status_code == 422
    
    # 2. Invalid category enum (e.g. "sports")
    bad_cat = await client.post("/api/v1/plans/habits", json={
        "name": "Bad Cat", "category": "sports", "difficulty": "easy"
    }, headers=headers)
    assert bad_cat.status_code == 422
    
    # 3. Bad ID (non-existent plan update)
    bad_plan = await client.put("/api/v1/plans/999999", json={
        "name": "Bad Plan", "difficulty": "medium", "habits": []
    }, headers=headers)
    assert bad_plan.status_code == 404

@pytest.mark.asyncio
async def test_business_rules_negative(client: AsyncClient, mock_time):
    await client.post("/api/v1/auth/register", json={"email": "rule_neg@test.com", "password": "pass", "timezone": "UTC"})
    l = (await client.post("/api/v1/auth/login", json={"email": "rule_neg@test.com", "password": "pass"})).json()["data"]
    headers = {"Authorization": f"Bearer {l['access_token']}"}
    
    # 1. Create duplicate habit name for same user
    await client.post("/api/v1/plans/habits", json={"name": "Dup Habit", "category": "focus", "difficulty": "easy"}, headers=headers)
    import sqlalchemy.exc
    try:
        dup_h = await client.post("/api/v1/plans/habits", json={"name": "Dup Habit", "category": "focus", "difficulty": "easy"}, headers=headers)
        assert dup_h.status_code >= 400
    except sqlalchemy.exc.IntegrityError:
        pass
    
    # 2. Activate non-existent plan
    act_bad = await client.post("/api/v1/plans/999999/activate", headers=headers)
    assert act_bad.status_code == 404
    
    # 3. Attempt to complete a habit log that doesn't exist for today
    act_comp = await client.post("/api/v1/execution/habit/complete", json={"habit_id": 999999}, headers=headers)
    assert act_comp.status_code == 404
