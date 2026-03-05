"""Tests for AI task-analysis integration (LangGraph + mock LLM)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.models.agent import Agent

TASK_PAYLOAD = {
    "title": "Build the dashboard",
    "description": "Create a dashboard with charts",
    "status": "todo",
    "priority": "high",
}


@pytest.mark.anyio
class TestAITaskAnalysis:
    async def test_creating_task_triggers_ai_comment(self, authed_client: AsyncClient):
        """POST /api/tasks should produce an AI comment from the assistant agent."""
        # Create a task
        resp = await authed_client.post("/api/tasks", json=TASK_PAYLOAD)
        assert resp.status_code == 201
        task = resp.json()

        # Fetch comments – there should be exactly one from the assistant agent
        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        assert resp.status_code == 200
        comments = resp.json()

        assert len(comments) == 1
        c = comments[0]
        assert c["author_type"] == "agent"
        assert c["author_name"] == "Thinker"
        assert "AI Analysis" in c["content"]
        assert c["parent_id"] is None

    async def test_ai_comment_contains_recommendations(self, authed_client: AsyncClient):
        resp = await authed_client.post("/api/tasks", json=TASK_PAYLOAD)
        task = resp.json()

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        content = resp.json()[0]["content"]

        # Verify the mock analysis includes expected sections
        for section in [
            "Priority assessment",
            "Estimated effort",
            "Suggested next steps",
            "Dependencies",
        ]:
            assert section in content

    async def test_ai_comment_is_agent_authored(self, authed_client: AsyncClient):
        resp = await authed_client.post("/api/tasks", json=TASK_PAYLOAD)
        task = resp.json()

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        c = resp.json()[0]

        assert c["user_id"] is None
        assert c["agent_id"] is not None

    async def test_ai_skips_when_assistant_agent_not_seeded(self):
        """When the assistant agent is not in the DB, no comment is created."""
        from app.ai.task_analysis import analyse_task_and_comment
        from tests.conftest import TestSession

        # Delete all agents so assistant agent is missing
        async with TestSession() as db:
            await db.execute(delete(Agent))
            await db.commit()

        # Run analysis — should return silently, no error
        await analyse_task_and_comment(
            task_id=str(uuid.uuid4()),
            title="Test task",
            description="Desc",
            priority="low",
            task_status="todo",
        )

        # No crash = success; the function returns None when agent is missing
