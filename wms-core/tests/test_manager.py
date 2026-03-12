"""Tests for the Manager agent pipeline."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.agent import Agent
from app.models.comment import Comment
from tests.conftest import TestSession

TASK_PAYLOAD = {
    "title": "Build dashboard",
    "description": "Create a dashboard with charts and metrics",
    "status": "todo",
    "priority": "medium",
}


async def create_task(client: AsyncClient, **overrides) -> dict:
    payload = {**TASK_PAYLOAD, **overrides}
    resp = await client.post("/api/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.anyio
class TestMockManagerLLM:
    """Tests for the MockManagerLLM behaviour."""

    async def test_mock_returns_updated_prompt(self):
        from app.ai.manager import MockManagerLLM

        llm = MockManagerLLM()
        from langchain_core.messages import HumanMessage

        prompt = (
            "Agent being reviewed: **executor**\n\n"
            "Current system prompt:\n# Executor Agent\n\n"
            "Recent conversation:\nuser: check this\nexecutor: done\n\n"
            "Instructions:\n..."
        )
        result = await llm.ainvoke([HumanMessage(content=prompt)])
        assert "# Executor Agent" in result.content
        assert "adapt your tone accordingly" in result.content

    async def test_mock_sync_generate(self):
        from langchain_core.messages import HumanMessage

        from app.ai.manager import MockManagerLLM

        llm = MockManagerLLM()
        result = llm.invoke([HumanMessage(content="Current system prompt:\nHello\n\nRecent conversation:\nhi")])
        assert "Hello" in result.content
        assert "adapt your tone accordingly" in result.content

    async def test_mock_no_marker(self):
        """When there's no 'Current system prompt:' marker, mock handles gracefully."""
        from langchain_core.messages import HumanMessage

        from app.ai.manager import MockManagerLLM

        llm = MockManagerLLM()
        result = await llm.ainvoke([HumanMessage(content="no structured input")])
        assert "adapt your tone accordingly" in result.content

    async def test_mock_empty_messages(self):
        from app.ai.manager import MockManagerLLM

        llm = MockManagerLLM()
        result = await llm.ainvoke([])
        assert "adapt your tone accordingly" in result.content


@pytest.mark.anyio
class TestBuildReviewPrompt:
    """Tests for build_review_prompt node."""

    async def test_basic_prompt(self):
        from app.ai.manager import build_review_prompt

        state = {
            "agent_key": "executor",
            "current_prompt": "# Executor",
            "conversation_context": "user: hi\nexecutor: hello",
            "system_prompt": "",
            "result": "",
        }
        out = build_review_prompt(state)
        assert "executor" in out["result"]
        assert "# Executor" in out["result"]
        assert "user: hi" in out["result"]
        assert "PROMPT_UNCHANGED" in out["result"]

    async def test_prompt_with_manager_persona(self):
        from app.ai.manager import build_review_prompt

        state = {
            "agent_key": "thinker",
            "current_prompt": "# Thinker",
            "conversation_context": "user: think about this",
            "system_prompt": "You are the meta-coach.",
            "result": "",
        }
        out = build_review_prompt(state)
        assert out["result"].startswith("You are the meta-coach.")


@pytest.mark.anyio
class TestCallManagerLLM:
    """Tests for call_manager_llm node."""

    async def test_call_returns_result(self):
        from app.ai.manager import MockManagerLLM, call_manager_llm, set_manager_llm

        set_manager_llm(MockManagerLLM())
        state = {
            "agent_key": "executor",
            "current_prompt": "# Executor",
            "conversation_context": "user: check\nexecutor: ok",
            "system_prompt": "",
            "result": "Current system prompt:\n# Executor\n\nRecent conversation:\nuser: check",
        }
        out = await call_manager_llm(state)
        assert "adapt your tone accordingly" in out["result"]


@pytest.mark.anyio
class TestManagerLLMFactory:
    """Tests for _build_manager_llm and related functions."""

    async def test_build_mock_provider(self):
        from unittest.mock import patch

        from app.ai.manager import MockManagerLLM, _build_manager_llm

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "mock"
            llm = _build_manager_llm()
        assert isinstance(llm, MockManagerLLM)

    async def test_get_manager_llm_lazy_init(self):
        from unittest.mock import patch

        from app.ai.manager import MockManagerLLM, _get_manager_llm, set_manager_llm

        set_manager_llm(None)
        try:
            with patch("app.core.config.settings") as mock_settings:
                mock_settings.LLM_PROVIDER = "mock"
                llm = _get_manager_llm()
            assert isinstance(llm, MockManagerLLM)
        finally:
            set_manager_llm(MockManagerLLM())

    async def test_build_ollama_success(self):
        from unittest.mock import MagicMock, patch

        from app.ai.manager import _build_manager_llm

        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "ollama"
            mock_settings.OLLAMA_MODEL = "qwen2.5:14b"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            with patch.dict("sys.modules", {"langchain_ollama": MagicMock(ChatOllama=mock_cls)}):
                llm = _build_manager_llm()
        assert llm is mock_instance

    async def test_build_ollama_failure_fallback(self):
        from unittest.mock import patch

        from app.ai.manager import MockManagerLLM, _build_manager_llm

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "ollama"
            mock_settings.OLLAMA_MODEL = "qwen2.5:14b"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            with patch.dict("sys.modules", {"langchain_ollama": None}):
                llm = _build_manager_llm()
        assert isinstance(llm, MockManagerLLM)


@pytest.mark.anyio
class TestReviewAndAdjust:
    """Tests for the review_and_adjust public API."""

    async def test_adjusts_agent_prompt(self, authed_client: AsyncClient):
        """Manager reviews conversation and updates agent's system prompt."""
        task = await create_task(authed_client)

        # Seed a comment so there's conversation context
        await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "Let's discuss this task"},
        )

        # Set a known prompt on executor
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.system_prompt = "# Executor Agent"
            await db.commit()

        from app.ai.manager import review_and_adjust

        result = await review_and_adjust(task["id"], "executor")
        assert result is not None
        assert "# Executor Agent" in result
        assert "adapt your tone accordingly" in result

        # Verify it was persisted
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            assert "adapt your tone accordingly" in agent.system_prompt

    async def test_no_change_when_no_comments(self, authed_client: AsyncClient):
        """Manager returns None when the task has no comments."""
        task = await create_task(authed_client)

        # Delete all auto-generated comments
        async with TestSession() as db:
            await db.execute(Comment.__table__.delete().where(Comment.task_id == task["id"]))
            await db.commit()

        from app.ai.manager import review_and_adjust

        result = await review_and_adjust(task["id"], "executor")
        assert result is None

    async def test_returns_none_for_missing_agent(self):
        """Manager returns None if the agent doesn't exist."""
        from app.ai.manager import review_and_adjust

        result = await review_and_adjust(str(uuid.uuid4()), "nonexistent_agent")
        assert result is None

    async def test_returns_none_for_inactive_agent(self, authed_client: AsyncClient):
        """Manager skips inactive agents."""
        task = await create_task(authed_client)

        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.is_active = False
            await db.commit()

        from app.ai.manager import review_and_adjust

        try:
            result = await review_and_adjust(task["id"], "executor")
            assert result is None
        finally:
            async with TestSession() as db:
                res = await db.execute(select(Agent).where(Agent.key == "executor"))
                agent = res.scalar_one()
                agent.is_active = True
                await db.commit()

    async def test_prompt_unchanged_path(self, authed_client: AsyncClient):
        """When the LLM returns PROMPT_UNCHANGED, no update is made."""
        from unittest.mock import AsyncMock

        from langchain_core.messages import AIMessage

        from app.ai.manager import PROMPT_UNCHANGED, review_and_adjust, set_manager_llm

        task = await create_task(authed_client)

        # Mock LLM that returns PROMPT_UNCHANGED
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=PROMPT_UNCHANGED))
        set_manager_llm(mock_llm)

        try:
            async with TestSession() as db:
                res = await db.execute(select(Agent).where(Agent.key == "executor"))
                agent = res.scalar_one()
                original_prompt = agent.system_prompt

            result = await review_and_adjust(task["id"], "executor")
            assert result is None

            # Verify prompt unchanged
            async with TestSession() as db:
                res = await db.execute(select(Agent).where(Agent.key == "executor"))
                agent = res.scalar_one()
                assert agent.system_prompt == original_prompt
        finally:
            from app.ai.manager import MockManagerLLM

            set_manager_llm(MockManagerLLM())

    async def test_uses_manager_persona(self, authed_client: AsyncClient):
        """Manager's own system_prompt is injected into the review prompt."""
        task = await create_task(authed_client)

        # Set Manager's persona
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "manager"))
            agent = res.scalar_one()
            agent.system_prompt = "You are the team meta-coach."
            await db.commit()

        from app.ai.manager import review_and_adjust

        # The review will use the manager's persona — just verify it runs OK
        result = await review_and_adjust(task["id"], "executor")
        assert result is not None


@pytest.mark.anyio
class TestManagerTriggeredByMention:
    """Tests that Manager is triggered after agent mention replies."""

    async def test_mention_triggers_manager_review(self, authed_client: AsyncClient):
        """After @Executor replies, Manager adjusts executor's prompt."""
        # Set a known prompt
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.system_prompt = "# Executor Agent"
            await db.commit()

        task = await create_task(authed_client)

        # Mention @Executor — triggers reply + Manager review
        await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Executor help with this"},
        )

        # Verify Manager adjusted the prompt
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            assert "adapt your tone accordingly" in agent.system_prompt

    async def test_manager_mention_reviews_all_agents(self, authed_client: AsyncClient):
        """@Manager mention triggers review of all non-manager agents."""
        # Set known prompts
        async with TestSession() as db:
            for key in ("executor", "thinker"):
                res = await db.execute(select(Agent).where(Agent.key == key))
                agent = res.scalar_one()
                agent.system_prompt = f"# {key.title()} Agent"
            await db.commit()

        task = await create_task(authed_client)

        await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Manager please review the agents"},
        )

        # Both executor and thinker should have updated prompts
        async with TestSession() as db:
            for key in ("executor", "thinker"):
                res = await db.execute(select(Agent).where(Agent.key == key))
                agent = res.scalar_one()
                assert "adapt your tone accordingly" in agent.system_prompt

    async def test_reply_to_agent_triggers_manager(self, authed_client: AsyncClient):
        """Replying to agent comment triggers Manager review via handle_agent_reply."""
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.system_prompt = "# Executor Agent"
            await db.commit()

        task = await create_task(authed_client)

        # First get an agent reply via @mention
        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Executor what's up?"},
        )
        assert resp.status_code == 201

        # Get the agent reply
        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()
        user_comment = next(c for c in comments if "@Executor" in c["content"])
        agent_reply = user_comment["replies"][0]

        # Reset prompt to test handle_agent_reply path
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.system_prompt = "# Executor Fresh"
            await db.commit()

        # Reply to agent comment (triggers handle_agent_reply + Manager review)
        await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "Can you elaborate?", "parent_id": agent_reply["id"]},
        )

        # Verify Manager adjusted the prompt
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            assert "adapt your tone accordingly" in agent.system_prompt


@pytest.mark.anyio
class TestManagerAgentSeeded:
    """Tests that the Manager agent is properly seeded."""

    async def test_manager_agent_exists(self):
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "manager"))
            agent = res.scalar_one_or_none()
            assert agent is not None
            assert agent.name == "Manager"
            assert agent.is_active is True


@pytest.mark.anyio
class TestParseSkillRequest:
    """Tests for parse_skill_request helper."""

    def test_basic_skill_request(self):
        from app.ai.manager import parse_skill_request

        result = parse_skill_request("@Manager please add skill to @Executor Agent that I prefer to go by bus")
        assert result is not None
        agent_key, skill = result
        assert agent_key == "Executor"
        assert skill == "I prefer to go by bus"

    def test_skill_request_lowercase(self):
        from app.ai.manager import parse_skill_request

        result = parse_skill_request("@Manager add skill to @thinker that always consider edge cases")
        assert result is not None
        assert result[0] == "thinker"
        assert result[1] == "always consider edge cases"

    def test_skill_request_with_trailing_dot(self):
        from app.ai.manager import parse_skill_request

        result = parse_skill_request("@Manager add skill to @Executor that I like short answers.")
        assert result is not None
        assert result[1] == "I like short answers"

    def test_no_skill_request(self):
        from app.ai.manager import parse_skill_request

        result = parse_skill_request("@Manager please review the agents")
        assert result is None

    def test_skill_request_missing_that(self):
        from app.ai.manager import parse_skill_request

        result = parse_skill_request("@Manager add skill to @Executor")
        assert result is None

    def test_skill_request_empty_skill(self):
        from app.ai.manager import parse_skill_request

        result = parse_skill_request("@Manager add skill to @Executor that ")
        assert result is None


@pytest.mark.anyio
class TestAddSkillToAgent:
    """Tests for add_skill_to_agent."""

    async def test_adds_skill_to_prompt(self):
        from app.ai.manager import add_skill_to_agent

        # Set a known prompt
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.system_prompt = "# Executor Agent"
            await db.commit()

        result = await add_skill_to_agent("executor", "I prefer to go by bus")
        assert result is not None
        assert "# Executor Agent" in result
        assert "- Remember: I prefer to go by bus" in result

        # Verify persisted
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            assert "- Remember: I prefer to go by bus" in agent.system_prompt

    async def test_does_not_duplicate_skill(self):
        from app.ai.manager import add_skill_to_agent

        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.system_prompt = "# Executor\n\n- Remember: I prefer to go by bus"
            await db.commit()

        result = await add_skill_to_agent("executor", "I prefer to go by bus")
        assert result is not None
        assert result.count("- Remember: I prefer to go by bus") == 1

    async def test_returns_none_for_missing_agent(self):
        from app.ai.manager import add_skill_to_agent

        result = await add_skill_to_agent("nonexistent", "some skill")
        assert result is None

    async def test_returns_none_for_inactive_agent(self):
        from app.ai.manager import add_skill_to_agent

        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.is_active = False
            await db.commit()

        try:
            result = await add_skill_to_agent("executor", "some skill")
            assert result is None
        finally:
            async with TestSession() as db:
                res = await db.execute(select(Agent).where(Agent.key == "executor"))
                agent = res.scalar_one()
                agent.is_active = True
                await db.commit()

    async def test_adds_skill_to_empty_prompt(self):
        from app.ai.manager import add_skill_to_agent

        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.system_prompt = ""
            await db.commit()

        result = await add_skill_to_agent("executor", "I like tests")
        assert result == "- Remember: I like tests"


@pytest.mark.anyio
class TestSkillViaManagerMention:
    """Integration: @Manager + skill request updates target agent."""

    async def test_manager_mention_adds_skill(self, authed_client: AsyncClient):
        """@Manager add skill to @Executor ... updates executor's prompt."""
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            agent.system_prompt = "# Executor Agent"
            await db.commit()

        task = await create_task(authed_client)

        await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Manager please add skill to @Executor Agent that I prefer to go by bus"},
        )

        # Verify executor's prompt now has the skill
        async with TestSession() as db:
            res = await db.execute(select(Agent).where(Agent.key == "executor"))
            agent = res.scalar_one()
            assert "- Remember: I prefer to go by bus" in agent.system_prompt

    async def test_manager_mention_without_skill_does_review(self, authed_client: AsyncClient):
        """@Manager without skill request falls back to review_and_adjust."""
        async with TestSession() as db:
            for key in ("executor", "thinker"):
                res = await db.execute(select(Agent).where(Agent.key == key))
                agent = res.scalar_one()
                agent.system_prompt = f"# {key.title()} Agent"
            await db.commit()

        task = await create_task(authed_client)

        await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Manager please review the agents"},
        )

        # Both should have the review tweak (not a skill line)
        async with TestSession() as db:
            for key in ("executor", "thinker"):
                res = await db.execute(select(Agent).where(Agent.key == key))
                agent = res.scalar_one()
                assert "adapt your tone accordingly" in agent.system_prompt
