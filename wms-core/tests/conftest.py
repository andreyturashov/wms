"""Shared test fixtures for the WMS backend test suite."""

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Import all models so their tables are registered with Base.metadata
from app.models import (
    agent as _agent_mod,
)
from app.models import (
    comment as _comment_mod,
)
from app.models import (
    task as _task_mod,
)
from app.models import (
    user as _user_mod,
)

_ = (_agent_mod, _comment_mod, _task_mod, _user_mod)

# ---------------------------------------------------------------------------
# Database fixtures – each test gets its own in-memory SQLite database
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"  # in-memory

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop them afterwards."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_default_agents_for_tests()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def seed_default_agents_for_tests():
    """Seed the four default agents using test DB session."""
    from app.main import DEFAULT_AGENTS
    from app.models.agent import Agent

    async with TestSession() as db:
        for a in DEFAULT_AGENTS:
            db.add(
                Agent(
                    id=str(uuid.uuid4()),
                    key=a["key"],
                    name=a["name"],
                    description=a["description"],
                    is_active=True,
                )
            )
        await db.commit()


async def _override_get_db() -> AsyncGenerator[AsyncSession]:
    async with TestSession() as session:
        yield session


# Override the DB dependency for the whole test suite
app.dependency_overrides[get_db] = _override_get_db

# Point the AI analysis module at the test session factory
from app.ai.task_analysis import set_session_factory

set_session_factory(TestSession)

# Point the agent-mention module at the test session factory
from app.ai.agent_mention import MockMentionLLM, set_mention_llm
from app.ai.agent_mention import set_session_factory as set_mention_session_factory

set_mention_session_factory(TestSession)
# Force mock LLM in tests so they never hit a real Ollama server
set_mention_llm(MockMentionLLM())


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


async def register_user(
    client: AsyncClient,
    email: str = "test@example.com",
    username: str = "testuser",
    password: str = "testpassword123",
) -> dict:
    """Register a user and return the JSON response (contains access_token)."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def authed_client(client: AsyncClient) -> AsyncClient:
    """Return the same client instance but with a valid auth header pre-set."""
    data = await register_user(client)
    token = data["access_token"]
    client.headers.update(auth_headers(token))
    return client
