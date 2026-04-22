from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.main import app
from app.models.user import User


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeAsyncSession:
    def __init__(self):
        self.users: list[User] = []

    async def execute(self, stmt):
        where = stmt.whereclause
        if where is None:
            return _FakeResult(None)

        column_name = where.left.name
        value = where.right.value

        if column_name == "email":
            for user in self.users:
                if user.email == value:
                    return _FakeResult(user)

        if column_name == "id":
            for user in self.users:
                if user.id == value:
                    return _FakeResult(user)

        return _FakeResult(None)

    def add(self, user: User) -> None:
        if user.id is None:
            user.id = uuid.uuid4()
        self.users.append(user)

    async def commit(self) -> None:
        return None

    async def refresh(self, _user: User) -> None:
        return None


@pytest_asyncio.fixture
async def test_client_and_db():
    db = FakeAsyncSession()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, db

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_success_hashes_password(test_client_and_db):
    client, db = test_client_and_db
    response = await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "Secret123", "name": "Test User"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Registered successfully"
    assert "user_id" in body

    stored_user = db.users[0]
    assert stored_user.password != "Secret123"
    assert verify_password("Secret123", stored_user.password) is True


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(test_client_and_db):
    client, db = test_client_and_db
    db.add(
        User(
            email="dup@example.com",
            password=hash_password("abc12345"),
            name="Dup User",
        )
    )

    response = await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "Secret123", "name": "Another User"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_login_invalid_credentials_same_message_for_email_and_password(test_client_and_db):
    client, db = test_client_and_db
    db.add(
        User(
            email="valid@example.com",
            password=hash_password("Correct123"),
            name="Valid User",
        )
    )

    wrong_email_response = await client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "Correct123"},
    )
    wrong_password_response = await client.post(
        "/api/auth/login",
        json={"email": "valid@example.com", "password": "WrongPassword"},
    )

    assert wrong_email_response.status_code == 401
    assert wrong_password_response.status_code == 401
    assert wrong_email_response.json()["detail"] == "Invalid credentials"
    assert wrong_password_response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_success_returns_bearer_and_me_is_protected(test_client_and_db):
    client, db = test_client_and_db
    db.add(
        User(
            email="auth@example.com",
            password=hash_password("Correct123"),
            name="Auth User",
        )
    )

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "auth@example.com", "password": "Correct123"},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    assert login_response.json()["token_type"] == "bearer"

    me_without_token = await client.get("/api/auth/me")
    assert me_without_token.status_code == 401

    me_with_token = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_with_token.status_code == 200
    me_body = me_with_token.json()
    assert me_body["email"] == "auth@example.com"
    assert me_body["name"] == "Auth User"
    assert me_body["user_id"] == str(db.users[0].id)