"""Tests for SQLAdmin authentication backend (app/admin.py)."""

from unittest.mock import MagicMock

import pytest
from jose import jwt
from starlette.requests import Request

from app.admin import ALL_VIEWS, AdminAuth, setup_admin
from app.api.auth import create_access_token, settings
from app.core.config import settings as app_settings
from tests.conftest import TestSession


@pytest.fixture
def auth_backend() -> AdminAuth:
    return AdminAuth(secret_key=app_settings.SECRET_KEY)


@pytest.fixture(autouse=True)
def _patch_admin_session(monkeypatch):
    """Make AdminAuth.login use the test DB instead of the production one."""
    monkeypatch.setattr("app.admin.AsyncSessionLocal", TestSession)


def _make_request(session: dict | None = None, form_data: dict | None = None) -> Request:
    """Build a minimal Starlette Request with controllable session and form."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/admin/login",
        "headers": [],
    }
    request = Request(scope)
    # Attach a mutable session dict
    request._session = session if session is not None else {}
    # Monkey-patch request.session property
    type(request).session = property(lambda self: self._session)

    if form_data is not None:

        async def _form():
            return form_data

        request._form = _form  # type: ignore[attr-defined]
        # Override .form() method
        request.form = _form  # type: ignore[method-assign]

    # Provide url_for (used by authenticate to build redirect URLs)
    request._url_for = lambda name, **_: "/admin/login"
    request.url_for = request._url_for  # type: ignore[method-assign]

    return request


class TestAdminAuthLogin:
    async def test_login_success(self, auth_backend: AdminAuth, authed_client):
        """Login with correct credentials returns True and sets session token."""
        request = _make_request(
            session={},
            form_data={"username": "test@example.com", "password": "testpassword123"},
        )
        result = await auth_backend.login(request)
        assert result is True
        assert "token" in request.session

        # Verify the token is valid JWT
        token = request.session["token"]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload.get("sub") is not None

    async def test_login_wrong_password(self, auth_backend: AdminAuth, authed_client):
        """Login with wrong password returns False."""
        request = _make_request(
            session={},
            form_data={"username": "test@example.com", "password": "wrongpassword"},
        )
        result = await auth_backend.login(request)
        assert result is False
        assert "token" not in request.session

    async def test_login_nonexistent_user(self, auth_backend: AdminAuth, setup_database):
        """Login with non-existent email returns False."""
        request = _make_request(
            session={},
            form_data={"username": "noone@example.com", "password": "whatever"},
        )
        result = await auth_backend.login(request)
        assert result is False

    async def test_login_empty_credentials(self, auth_backend: AdminAuth, setup_database):
        """Login with empty credentials returns False."""
        request = _make_request(
            session={},
            form_data={"username": "", "password": ""},
        )
        result = await auth_backend.login(request)
        assert result is False


class TestAdminAuthLogout:
    async def test_logout_clears_session(self, auth_backend: AdminAuth):
        """Logout clears the session and returns True."""
        session = {"token": "some-jwt-token"}
        request = _make_request(session=session)
        result = await auth_backend.logout(request)
        assert result is True
        assert request.session == {}


class TestAdminAuthAuthenticate:
    async def test_authenticate_valid_token(self, auth_backend: AdminAuth, authed_client):
        """A valid JWT in the session passes authentication."""
        from datetime import timedelta

        token = create_access_token(
            data={"sub": "some-user-id"},
            expires_delta=timedelta(minutes=30),
        )
        request = _make_request(session={"token": token})
        result = await auth_backend.authenticate(request)
        assert result is True

    async def test_authenticate_no_token(self, auth_backend: AdminAuth):
        """Missing token redirects to login."""
        request = _make_request(session={})
        result = await auth_backend.authenticate(request)
        # Should return a RedirectResponse
        assert hasattr(result, "status_code")
        assert result.status_code == 302

    async def test_authenticate_invalid_token(self, auth_backend: AdminAuth):
        """Invalid JWT redirects to login."""
        request = _make_request(session={"token": "not-a-valid-jwt"})
        result = await auth_backend.authenticate(request)
        assert hasattr(result, "status_code")
        assert result.status_code == 302

    async def test_authenticate_token_without_sub(self, auth_backend: AdminAuth):
        """JWT without 'sub' claim redirects to login."""
        # Create a token without sub
        token = jwt.encode({"data": "no-sub"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        request = _make_request(session={"token": token})
        result = await auth_backend.authenticate(request)
        assert hasattr(result, "status_code")
        assert result.status_code == 302


class TestSetupAdmin:
    def test_setup_admin_returns_admin_instance(self):
        """setup_admin() creates an Admin with all model views registered."""

        mock_app = MagicMock()
        mock_engine = MagicMock()
        admin = setup_admin(mock_app, mock_engine)
        assert admin is not None

    def test_all_views_contains_expected_views(self):
        """ALL_VIEWS includes User, Task, Agent, Comment admin views."""
        view_names = [v.__name__ for v in ALL_VIEWS]
        assert "UserAdmin" in view_names
        assert "TaskAdmin" in view_names
        assert "AgentAdmin" in view_names
        assert "CommentAdmin" in view_names
