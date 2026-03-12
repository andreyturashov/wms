"""Tests for startup / lifecycle logic and the real get_db generator."""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.main import (
    backfill_task_agent_ids,
    create_tables,
    ensure_agent_system_prompt_column,
    ensure_task_agent_fk_column,
    ensure_task_assigned_user_fk_column,
    seed_default_agents,
)
from app.models.agent import Agent
from app.models.user import User

# We need a SEPARATE in-memory engine so we don't interfere with conftest's.
# The startup helpers use their own AsyncSessionLocal internally, so we
# monkey-patch that to point at our test engine.

_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
_TestSession = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _patch_session(monkeypatch):
    """Redirect app.main and app.db.session to our private in-memory engine."""
    import app.db.session as sess_mod
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "engine", _engine)
    monkeypatch.setattr(main_mod, "AsyncSessionLocal", _TestSession)
    monkeypatch.setattr(sess_mod, "engine", _engine)
    monkeypatch.setattr(sess_mod, "AsyncSessionLocal", _TestSession)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# seed_default_agents
# ---------------------------------------------------------------------------


class TestSeedDefaultAgents:
    async def test_seeds_agents(self):
        await seed_default_agents()
        async with _TestSession() as db:
            result = await db.execute(select(Agent))
            agents = result.scalars().all()
        keys = {a.key for a in agents}
        assert keys == {"executor", "thinker", "manager"}

    async def test_seeds_system_prompt_from_file(self):
        """seed_default_agents populates system_prompt from Professional.md."""
        await seed_default_agents()
        async with _TestSession() as db:
            result = await db.execute(select(Agent))
            agents = {a.key: a for a in result.scalars().all()}
        assert "Executor Agent" in agents["executor"].system_prompt
        assert "Thinker Agent" in agents["thinker"].system_prompt

    async def test_backfills_empty_system_prompt(self):
        """Re-seeding backfills system_prompt if it was empty."""
        # First seed
        await seed_default_agents()
        # Clear the system_prompt
        async with _TestSession() as db:
            result = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = result.scalar_one()
            agent.system_prompt = ""
            await db.commit()
        # Re-seed should backfill
        await seed_default_agents()
        async with _TestSession() as db:
            result = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = result.scalar_one()
        assert "Executor Agent" in agent.system_prompt

    async def test_does_not_overwrite_custom_prompt(self):
        """Re-seeding should NOT overwrite a non-empty custom system_prompt."""
        await seed_default_agents()
        async with _TestSession() as db:
            result = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = result.scalar_one()
            agent.system_prompt = "Custom prompt"
            await db.commit()
        await seed_default_agents()
        async with _TestSession() as db:
            result = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = result.scalar_one()
        assert agent.system_prompt == "Custom prompt"

    async def test_idempotent(self):
        await seed_default_agents()
        await seed_default_agents()  # second run should not duplicate
        async with _TestSession() as db:
            result = await db.execute(select(Agent))
            agents = result.scalars().all()
        assert len(agents) == 3

    async def test_removes_obsolete_agents(self):
        """Agents whose key is not in DEFAULT_AGENTS should be removed."""
        # Seed defaults first
        await seed_default_agents()

        # Insert an extra agent that is NOT in DEFAULT_AGENTS
        async with _TestSession() as db:
            db.add(
                Agent(
                    id=str(uuid.uuid4()),
                    key="obsolete_bot",
                    name="Obsolete Bot",
                    description="Should be removed",
                    is_active=True,
                )
            )
            await db.commit()

        # Verify the extra agent exists
        async with _TestSession() as db:
            result = await db.execute(select(Agent))
            agents = result.scalars().all()
        assert len(agents) == 4

        # Re-run seed — obsolete agent should be removed
        await seed_default_agents()

        async with _TestSession() as db:
            result = await db.execute(select(Agent))
            agents = result.scalars().all()
        keys = {a.key for a in agents}
        assert keys == {"executor", "thinker", "manager"}
        assert len(agents) == 3


# ---------------------------------------------------------------------------
# ensure_agent_system_prompt_column
# ---------------------------------------------------------------------------


class TestEnsureAgentSystemPromptColumn:
    async def test_noop_when_column_exists(self):
        """Column exists from metadata.create_all — should be a no-op."""
        async with _engine.begin() as conn:
            await ensure_agent_system_prompt_column(conn)
            info = await conn.execute(text("PRAGMA table_info(agents)"))
            cols = {row[1] for row in info.fetchall()}
        assert "system_prompt" in cols

    async def test_adds_column_when_missing(self):
        """Recreate agents table without system_prompt, verify migration adds it."""
        async with _engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS agents"))
            await conn.execute(
                text(
                    "CREATE TABLE agents ("
                    "  id VARCHAR PRIMARY KEY,"
                    "  key VARCHAR NOT NULL,"
                    "  name VARCHAR NOT NULL,"
                    "  description TEXT DEFAULT '',"
                    "  is_active BOOLEAN DEFAULT 1,"
                    "  created_at DATETIME,"
                    "  updated_at DATETIME"
                    ")"
                )
            )
            await ensure_agent_system_prompt_column(conn)
            info = await conn.execute(text("PRAGMA table_info(agents)"))
            cols = {row[1] for row in info.fetchall()}
        assert "system_prompt" in cols


# ---------------------------------------------------------------------------
# ensure_task_agent_fk_column
# ---------------------------------------------------------------------------


class TestEnsureAgentFkColumn:
    async def test_creates_column_and_index(self):
        # Column already exists (created by metadata.create_all), but
        # calling ensure_task_agent_fk_column should be a no-op success.
        async with _engine.begin() as conn:
            await ensure_task_agent_fk_column(conn)
            info = await conn.execute(text("PRAGMA table_info(tasks)"))
            cols = {row[1] for row in info.fetchall()}
        assert "agent_id" in cols

    async def test_adds_column_when_missing(self):
        """Drop agent_id and verify ensure_task_agent_fk_column re-creates it."""
        # Recreate the tasks table without agent_id column
        async with _engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS tasks"))
            await conn.execute(
                text(
                    "CREATE TABLE tasks ("
                    "  id VARCHAR PRIMARY KEY,"
                    "  title VARCHAR NOT NULL,"
                    "  description TEXT DEFAULT '',"
                    "  status VARCHAR DEFAULT 'todo',"
                    "  priority VARCHAR DEFAULT 'medium',"
                    "  due_date VARCHAR,"
                    "  user_id VARCHAR NOT NULL"
                    ")"
                )
            )
            await ensure_task_agent_fk_column(conn)
            info = await conn.execute(text("PRAGMA table_info(tasks)"))
            cols = {row[1] for row in info.fetchall()}
        assert "agent_id" in cols


# ---------------------------------------------------------------------------
# ensure_task_assigned_user_fk_column
# ---------------------------------------------------------------------------


class TestEnsureAssignedUserFkColumn:
    async def test_creates_column_and_index(self):
        """Column exists from metadata.create_all — should be a no-op."""
        async with _engine.begin() as conn:
            await ensure_task_assigned_user_fk_column(conn)
            info = await conn.execute(text("PRAGMA table_info(tasks)"))
            cols = {row[1] for row in info.fetchall()}
        assert "assigned_user_id" in cols

    async def test_adds_column_when_missing(self):
        """Drop assigned_user_id and verify it's re-created."""
        async with _engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS tasks"))
            await conn.execute(
                text(
                    "CREATE TABLE tasks ("
                    "  id VARCHAR PRIMARY KEY,"
                    "  title VARCHAR NOT NULL,"
                    "  description TEXT DEFAULT '',"
                    "  status VARCHAR DEFAULT 'todo',"
                    "  priority VARCHAR DEFAULT 'medium',"
                    "  due_date VARCHAR,"
                    "  user_id VARCHAR NOT NULL,"
                    "  agent_id VARCHAR"
                    ")"
                )
            )
            await ensure_task_assigned_user_fk_column(conn)
            info = await conn.execute(text("PRAGMA table_info(tasks)"))
            cols = {row[1] for row in info.fetchall()}
        assert "assigned_user_id" in cols


# ---------------------------------------------------------------------------
# backfill_task_agent_ids
# ---------------------------------------------------------------------------


class TestBackfillAgentIds:
    async def test_backfill_skips_when_no_legacy_column(self):
        """No assigned_agent column → backfill is a no-op (no error)."""
        await seed_default_agents()
        await backfill_task_agent_ids()  # should not raise

    async def test_backfill_with_legacy_column(self):
        """When assigned_agent column exists, tasks should get agent_id backfilled."""
        await seed_default_agents()

        # Add a legacy assigned_agent column
        async with _engine.begin() as conn:
            await conn.execute(text("ALTER TABLE tasks ADD COLUMN assigned_agent VARCHAR"))

        # Create a user and a task with only assigned_agent set
        user_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        async with _TestSession() as db:
            db.add(User(id=user_id, email="bf@test.com", username="bf", password_hash="x"))
            await db.flush()
            await db.execute(
                text(
                    "INSERT INTO tasks (id, title, status, priority, user_id, assigned_agent) "
                    "VALUES (:id, :title, :status, :priority, :user_id, :assigned_agent)"
                ),
                {
                    "id": task_id,
                    "title": "legacy",
                    "status": "todo",
                    "priority": "medium",
                    "user_id": user_id,
                    "assigned_agent": "executor",
                },
            )
            await db.commit()

        await backfill_task_agent_ids()

        # Verify agent_id was set
        async with _TestSession() as db:
            result = await db.execute(text("SELECT agent_id FROM tasks WHERE id = :id"), {"id": task_id})
            row = result.fetchone()
        assert row is not None
        assert row[0] is not None  # agent_id should be populated


# ---------------------------------------------------------------------------
# create_tables  (integration of all startup steps)
# ---------------------------------------------------------------------------


class TestCreateTables:
    async def test_full_startup(self):
        await create_tables()
        async with _TestSession() as db:
            result = await db.execute(select(Agent))
            agents = result.scalars().all()
        assert len(agents) == 3


# ---------------------------------------------------------------------------
# get_db generator
# ---------------------------------------------------------------------------


class TestGetDb:
    async def test_get_db_yields_session(self):
        from app.db.session import get_db

        gen = get_db()
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession)
        # cleanup
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass
