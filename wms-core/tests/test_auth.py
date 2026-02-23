"""Tests for the authentication API (/api/auth)."""

import pytest
from httpx import AsyncClient

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
        resp = await client.get(
            "/api/auth/me", headers=auth_headers(data["access_token"])
        )
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
