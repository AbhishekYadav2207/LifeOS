import pytest
from app.models.user import User
from sqlalchemy.future import select

@pytest.mark.asyncio
async def test_register_user(client, db_session):
    response = await client.post("/api/v1/auth/register", json={
        "email": "register@test.com",
        "password": "strongpassword123",
        "timezone": "UTC"
    })
    data = response.json()
    assert response.status_code == 201
    assert data["success"] == True
    assert data["data"]["email"] == "register@test.com"
    
    # DB integrity verification
    res = await db_session.execute(select(User).where(User.email == "register@test.com"))
    assert res.scalars().first() is not None

@pytest.mark.asyncio
async def test_register_duplicate_user(client):
    payload = {"email": "dup@test.com", "password": "pass", "timezone": "UTC"}
    await client.post("/api/v1/auth/register", json=payload)
    response2 = await client.post("/api/v1/auth/register", json=payload)
    
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Email already registered"

@pytest.mark.asyncio
async def test_login_user(client):
    payload = {"email": "login@test.com", "password": "pass", "timezone": "UTC"}
    await client.post("/api/v1/auth/register", json=payload)
    
    response = await client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "pass"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "access_token" in data["data"]

@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "wrong@test.com",
        "password": "wrong"
    })
    assert response.status_code == 401
