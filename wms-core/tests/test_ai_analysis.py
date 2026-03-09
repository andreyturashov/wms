"""Tests for AI task-analysis integration (LangGraph + mock LLM)."""

import uuid
from unittest.mock import patch

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
    async def test_creating_task_triggers_ai_comments(self, authed_client: AsyncClient):
        """POST /api/tasks should produce AI comments from both agents."""
        resp = await authed_client.post("/api/tasks", json=TASK_PAYLOAD)
        assert resp.status_code == 201
        task = resp.json()

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        assert resp.status_code == 200
        comments = resp.json()

        assert len(comments) == 2
        author_names = {c["author_name"] for c in comments}
        assert author_names == {"Executor", "Thinker"}
        for c in comments:
            assert c["author_type"] == "agent"
            assert c["parent_id"] is None

    async def test_executor_comment_contains_plan(self, authed_client: AsyncClient):
        resp = await authed_client.post("/api/tasks", json=TASK_PAYLOAD)
        task = resp.json()

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        executor_comment = next(c for c in comments if c["author_name"] == "Executor")
        assert "straightforward" in executor_comment["content"]
        assert "test coverage" in executor_comment["content"]

    async def test_thinker_comment_contains_analysis(self, authed_client: AsyncClient):
        resp = await authed_client.post("/api/tasks", json=TASK_PAYLOAD)
        task = resp.json()

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        thinker_comment = next(c for c in comments if c["author_name"] == "Thinker")
        assert "edge cases" in thinker_comment["content"]
        assert "broader refactor" in thinker_comment["content"]

    async def test_ai_comments_are_agent_authored(self, authed_client: AsyncClient):
        resp = await authed_client.post("/api/tasks", json=TASK_PAYLOAD)
        task = resp.json()

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        for c in resp.json():
            assert c["user_id"] is None
            assert c["agent_id"] is not None

    async def test_ai_skips_when_agents_not_seeded(self):
        """When no agents are in the DB, no comments are created."""
        from app.ai.task_analysis import analyse_task_and_comment
        from tests.conftest import TestSession

        async with TestSession() as db:
            await db.execute(delete(Agent))
            await db.commit()

        await analyse_task_and_comment(
            task_id=str(uuid.uuid4()),
            title="Test task",
            description="Desc",
            priority="low",
            task_status="todo",
        )

    async def test_graph_exception_is_caught_and_logged(self):
        """When the LangGraph invocation raises, analyse_task_and_comment logs and continues."""
        from app.ai.task_analysis import MockLLM, analyse_task_and_comment, set_llm

        class _BrokenLLM(MockLLM):
            def _generate(self, messages, stop=None, **kwargs):
                raise RuntimeError("boom")

        set_llm(_BrokenLLM())
        try:
            await analyse_task_and_comment(
                task_id=str(uuid.uuid4()),
                title="Broken",
                description="desc",
                priority="low",
                task_status="todo",
            )
        finally:
            set_llm(MockLLM())

    async def test_build_llm_unknown_provider_falls_back_to_mock(self):
        """An unrecognised LLM_PROVIDER value should fall back to MockLLM."""
        from app.ai.task_analysis import MockLLM, _build_llm

        with patch("app.ai.task_analysis.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "unknown_provider"
            llm = _build_llm()

        assert isinstance(llm, MockLLM)

    async def test_load_professional_md_returns_content(self):
        """load_professional_md returns the markdown content for a valid key."""
        from app.ai.task_analysis import load_professional_md

        content = load_professional_md("executor")
        assert "Executor Agent" in content

        content = load_professional_md("thinker")
        assert "Thinker Agent" in content

    async def test_load_professional_md_missing_agent_returns_empty(self):
        """load_professional_md returns empty string for unknown key."""
        from app.ai.task_analysis import load_professional_md

        content = load_professional_md("nonexistent_agent")
        assert content == ""

    async def test_mock_llm_generic_fallback_without_system_prompt(self):
        """MockLLM returns generic AI Analysis when no system prompt is provided."""
        from langchain_core.messages import HumanMessage

        from app.ai.task_analysis import MockLLM

        llm = MockLLM()
        result = llm.invoke([HumanMessage(content="Analyse this task")])
        assert "well-scoped" in result.content
        assert "subtasks" in result.content

    async def test_mock_llm_executor_branch_with_system_message(self):
        """MockLLM returns Executor-specific response when system prompt contains '# Executor Agent'."""
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.ai.task_analysis import MockLLM

        llm = MockLLM()
        result = llm.invoke(
            [
                SystemMessage(content="# Executor Agent\nYou are the executor."),
                HumanMessage(content="Analyse this task"),
            ]
        )
        assert "test coverage" in result.content
        assert "straightforward" in result.content

    async def test_mock_llm_thinker_branch_with_system_message(self):
        """MockLLM returns Thinker-specific response when system prompt contains '# Thinker Agent'."""
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.ai.task_analysis import MockLLM

        llm = MockLLM()
        result = llm.invoke(
            [
                SystemMessage(content="# Thinker Agent\nYou are the thinker."),
                HumanMessage(content="Analyse this task"),
            ]
        )
        assert "edge cases" in result.content
        assert "broader refactor" in result.content

    async def test_get_llm_returns_current_instance(self):
        """_get_llm returns the currently set LLM instance."""
        from app.ai.task_analysis import MockLLM, _get_llm, set_llm

        original = _get_llm()
        custom = MockLLM()
        set_llm(custom)
        try:
            assert _get_llm() is custom
        finally:
            set_llm(original)

    async def test_build_prompt_directly(self):
        """build_prompt populates the result field with a formatted prompt."""
        from app.ai.task_analysis import build_prompt

        state = {
            "task_title": "My Task",
            "task_description": "Do something",
            "task_priority": "high",
            "task_status": "todo",
            "system_prompt": "",
            "result": "",
        }
        out = build_prompt(state)
        assert "My Task" in out["result"]
        assert "Do something" in out["result"]
        assert "high" in out["result"]
        assert "todo" in out["result"]

    async def test_build_prompt_no_description(self):
        """build_prompt shows '(none)' when description is empty."""
        from app.ai.task_analysis import build_prompt

        state = {
            "task_title": "T",
            "task_description": "",
            "task_priority": "low",
            "task_status": "done",
            "system_prompt": "",
            "result": "",
        }
        out = build_prompt(state)
        assert "(none)" in out["result"]

    async def test_call_llm_directly(self):
        """call_llm invokes the LLM and stores the response in state['result']."""
        from app.ai.task_analysis import MockLLM, call_llm, set_llm

        set_llm(MockLLM())
        state = {
            "task_title": "Test",
            "task_description": "desc",
            "task_priority": "medium",
            "task_status": "todo",
            "system_prompt": "# Executor Agent",
            "result": "Analyse this task please",
        }
        out = call_llm(state)
        assert "straightforward" in out["result"]

    async def test_call_llm_without_system_prompt(self):
        """call_llm works without a system prompt."""
        from app.ai.task_analysis import MockLLM, call_llm, set_llm

        set_llm(MockLLM())
        state = {
            "task_title": "Test",
            "task_description": "desc",
            "task_priority": "medium",
            "task_status": "todo",
            "system_prompt": "",
            "result": "Analyse this",
        }
        out = call_llm(state)
        assert "well-scoped" in out["result"]
