import pytest
from app.models.enums import HabitCategory
from tests.utils import create_test_user, create_test_habit

@pytest.mark.asyncio
async def test_create_habit(client, db_session):
    user = await create_test_user(db_session)
    response = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    token = response.json()["data"]["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "name": "Meditation",
        "category": "mind",
        "difficulty": "medium",
        "base_score": 20
    }
    
    res = await client.post("/api/v1/plans/habits", json=payload, headers=headers)
    assert res.status_code == 200
    _data = res.json()["data"]
    assert _data["name"] == "Meditation"
    assert _data["category"] == "mind"

@pytest.mark.asyncio
async def test_create_plan_and_assign(client, db_session):
    user = await create_test_user(db_session, email="plan@test.com")
    habit = await create_test_habit(db_session, category=HabitCategory.health)
    
    response = await client.post("/api/v1/auth/login", json={"email": "plan@test.com", "password": "password"})
    token = response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create a plan
    plan_payload = {
        "name": "Morning Routine",
        "is_public": True,
        "difficulty": "medium",
        "habits": [
            {
                "habit_id": habit.id,
                "start_time": "08:00:00",
                "end_time": "12:00:00"
            }
        ]
    }
    plan_res = await client.post("/api/v1/plans/", json=plan_payload, headers=headers)
    assert plan_res.status_code == 200
    plan_id = plan_res.json()["data"]["id"]
    
    # 2. Assign plan
    assign_res = await client.post("/api/v1/plans/select-plan", json={"plan_id": plan_id}, headers=headers)
    assert assign_res.status_code == 200
    assert "successfully" in assign_res.json()["message"]
    
@pytest.mark.asyncio
async def test_assign_invalid_plan(client, db_session):
    user = await create_test_user(db_session, email="invalid@test.com")
    response = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "password"})
    token = response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    res = await client.post("/api/v1/plans/select-plan", json={"plan_id": 9999}, headers=headers)
    assert res.status_code == 404
