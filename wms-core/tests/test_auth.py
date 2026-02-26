"""Tests for the authentication API (/api/auth)."""

from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from tests.conftest import auth_headers, register_user

# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        data = await register_user(client, email="new@example.com", username="newuser")
        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert data["user"]["email"] == "new@example.com"
        assert data["user"]["username"] == "newuser"
        assert "id" in data["user"]

    async def test_register_duplicate_email(self, client: AsyncClient):
        await register_user(client, email="dup@example.com")
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "dup@example.com",
                "username": "other",
                "password": "pass123",
            },
        )
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "username": "u", "password": "pass123"},
        )
        assert resp.status_code == 422

    async def test_register_missing_fields(self, client: AsyncClient):
        resp = await client.post("/api/auth/register", json={"email": "a@b.com"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        await register_user(client, email="login@example.com", password="secret123")
        resp = await client.post(
            "/api/auth/login",
            data={"username": "login@example.com", "password": "secret123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert "access_token" in body
        assert body["user"]["email"] == "login@example.com"

    async def test_login_wrong_password(self, client: AsyncClient):
        await register_user(client, email="wp@example.com", password="correct")
        resp = await client.post(
            "/api/auth/login",
            data={"username": "wp@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post(
            "/api/auth/login",
            data={"username": "nobody@example.com", "password": "any"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


class TestMe:
    async def test_me_success(self, client: AsyncClient):
        data = await register_user(client, email="me@example.com", username="meuser")
        resp = await client.get("/api/auth/me", headers=auth_headers(data["access_token"]))
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "me@example.com"
        assert body["username"] == "meuser"

    async def test_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_me_invalid_token(self, client: AsyncClient):
        resp = await client.get("/api/auth/me", headers=auth_headers("bogus-token"))
        assert resp.status_code == 401

    async def test_me_token_without_sub(self, client: AsyncClient):
        """Token with valid JWT but no 'sub' claim should be rejected."""
        token = jwt.encode({"data": "no-sub"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        resp = await client.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 401

    async def test_me_token_for_nonexistent_user(self, client: AsyncClient):
        """Token referencing a user id that doesn't exist in DB."""
        token = jwt.encode(
            {"sub": "nonexistent-user-id"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        resp = await client.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Auth helpers (unit)
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_default_expiry(self):
        """create_access_token without expires_delta uses 15-min default."""
        from app.api.auth import create_access_token

        token = create_access_token(data={"sub": "u1"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "u1"
        assert "exp" in payload


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------


class TestUtilityEndpoints:
    async def test_root(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json()["message"] == "WMS API is running"

    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# GET /api/auth/users
# ---------------------------------------------------------------------------


class TestListUsers:
    async def test_list_users_success(self, client: AsyncClient):
        data = await register_user(client, email="u1@example.com", username="alice")
        await register_user(client, email="u2@example.com", username="bob")
        resp = await client.get("/api/auth/users", headers=auth_headers(data["access_token"]))
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) == 2
        usernames = [u["username"] for u in users]
        assert "alice" in usernames
        assert "bob" in usernames

    async def test_list_users_ordered_by_username(self, client: AsyncClient):
        data = await register_user(client, email="z@example.com", username="zoe")
        await register_user(client, email="a@example.com", username="anna")
        resp = await client.get("/api/auth/users", headers=auth_headers(data["access_token"]))
        users = resp.json()
        assert users[0]["username"] == "anna"
        assert users[1]["username"] == "zoe"

    async def test_list_users_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/auth/users")
        assert resp.status_code == 401

    async def test_list_users_response_shape(self, client: AsyncClient):
        data = await register_user(client, email="s@example.com", username="sam")
        resp = await client.get("/api/auth/users", headers=auth_headers(data["access_token"]))
        user = resp.json()[0]
        assert "id" in user
        assert "email" in user
        assert "username" in user
        # Should NOT expose password_hash
        assert "password_hash" not in user
        assert "password" not in user
