import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_user_registration_and_login(client: AsyncClient):
    # Register user
    email = "test_auth_user@test.com"
    payload = {
        "email": email,
        "password": "securepassword123",
        "timezone": "America/New_York"
    }
    
    reg_resp = await client.post("/api/v1/auth/register", json=payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["success"] is True
    assert reg_data["data"]["email"] == email
    assert reg_data["data"]["timezone"] == "America/New_York"
    assert "id" in reg_data["data"]
    
    # Try to register duplicate email
    dup_resp = await client.post("/api/v1/auth/register", json=payload)
    assert dup_resp.status_code == 400
    assert "detail" in dup_resp.json()
    
    # Login user
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "securepassword123"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["success"] is True
    assert "access_token" in login_data["data"]
    assert login_data["data"]["token_type"] == "bearer"
    assert login_data["data"]["has_active_plan"] is False
    assert login_data["data"]["active_plan_id"] is None
    
    # Try login with invalid password
    bad_login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "wrongpassword"
    })
    assert bad_login.status_code == 401
