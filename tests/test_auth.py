import pytest

@pytest.mark.asyncio
async def test_register_user(client):
    response = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "strongpassword123",
        "timezone": "UTC"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["success"] == True
    assert data["data"]["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_login_user(client):
    # Register first
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "loginpassword123",
        "timezone": "UTC"
    })
    
    # Login
    response = await client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "loginpassword123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "access_token" in data["data"]
