import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.admin import setup_admin
from app.api import agents, auth, comments, tasks
from app.core.config import settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine

# Configure logging for the whole app
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# Import models BEFORE creating tables to ensure they are registered with Base
from app.models import agent, comment, task, user  # noqa: E402
from app.models.agent import Agent  # noqa: E402

_ = (user, task, agent, comment)

DEFAULT_AGENTS = [
    {
        "key": "executor",
        "name": "Executor",
        "description": "Executes task automation, scheduling, and notifications.",
    },
    {
        "key": "thinker",
        "name": "Thinker",
        "description": "Analyses tasks, provides recommendations, and generates insights.",
    },
    {
        "key": "manager",
        "name": "Manager",
        "description": "Reviews conversations and adjusts other agents' system prompts.",
    },
]


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_task_agent_fk_column(conn)
        await ensure_task_assigned_user_fk_column(conn)
        await ensure_agent_system_prompt_column(conn)

    await seed_default_agents()
    await backfill_task_agent_ids()


async def ensure_task_agent_fk_column(conn) -> None:
    table_info = await conn.execute(text("PRAGMA table_info(tasks)"))
    columns = {row[1] for row in table_info.fetchall()}
    if "agent_id" not in columns:
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN agent_id VARCHAR"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_agent_id ON tasks (agent_id)"))


async def ensure_task_assigned_user_fk_column(conn) -> None:
    table_info = await conn.execute(text("PRAGMA table_info(tasks)"))
    columns = {row[1] for row in table_info.fetchall()}
    if "assigned_user_id" not in columns:
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN assigned_user_id VARCHAR"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_assigned_user_id ON tasks (assigned_user_id)"))


async def ensure_agent_system_prompt_column(conn) -> None:
    table_info = await conn.execute(text("PRAGMA table_info(agents)"))
    columns = {row[1] for row in table_info.fetchall()}
    if "system_prompt" not in columns:
        await conn.execute(text("ALTER TABLE agents ADD COLUMN system_prompt TEXT DEFAULT ''"))


async def seed_default_agents() -> None:
    from app.ai.task_analysis import load_professional_md

    allowed_keys = {a["key"] for a in DEFAULT_AGENTS}

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Agent))
        existing_agents = {a.key: a for a in existing.scalars().all()}

        # Remove agents that are no longer in DEFAULT_AGENTS
        for key, agent in existing_agents.items():
            if key not in allowed_keys:
                await db.delete(agent)

        # Add missing default agents
        for default_agent in DEFAULT_AGENTS:
            if default_agent["key"] in existing_agents:
                # Backfill system_prompt if empty
                existing_agent = existing_agents[default_agent["key"]]
                if not existing_agent.system_prompt:
                    existing_agent.system_prompt = load_professional_md(default_agent["key"])
                continue

            db.add(
                Agent(
                    id=str(uuid.uuid4()),
                    key=default_agent["key"],
                    name=default_agent["name"],
                    description=default_agent["description"],
                    system_prompt=load_professional_md(default_agent["key"]),
                    is_active=True,
                )
            )

        await db.commit()


async def backfill_task_agent_ids() -> None:
    async with AsyncSessionLocal() as db:
        table_info = await db.execute(text("PRAGMA table_info(tasks)"))
        columns = {row[1] for row in table_info.fetchall()}
        if "assigned_agent" not in columns:
            return

        existing = await db.execute(select(Agent.id, Agent.key))
        key_to_id = {row[1]: row[0] for row in existing.fetchall()}

        for key, agent_id in key_to_id.items():
            await db.execute(
                text(
                    """
                    UPDATE tasks
                    SET agent_id = :agent_id
                    WHERE assigned_agent = :agent_key
                      AND (agent_id IS NULL OR agent_id = '')
                    """
                ),
                {"agent_id": agent_id, "agent_key": key},
            )

        await db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_tables()
    yield


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(comments.router, prefix="/api/tasks", tags=["comments"])
app.include_router(comments.comments_router, prefix="/api/comments", tags=["comments"])

# Admin panel at /admin
setup_admin(app, engine)


@app.get("/")
def root():  # pragma: no cover – tested via test_auth.py
    return {"message": "WMS API is running"}


@app.get("/health")
def health_check():  # pragma: no cover – tested via test_auth.py
    return {"status": "healthy"}
