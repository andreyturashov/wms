"""Tests for agent mention reactions in comments."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.models.agent import Agent

TASK_PAYLOAD = {
    "title": "Implement login page",
    "description": "Build a login page with email and password fields",
    "status": "todo",
    "priority": "high",
}


async def create_task(client: AsyncClient, **overrides) -> dict:
    payload = {**TASK_PAYLOAD, **overrides}
    resp = await client.post("/api/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.anyio
class TestAgentMentionReaction:
    async def test_mention_executor_triggers_reply(self, authed_client: AsyncClient):
        """Mentioning @Executor in a comment should produce an agent reply."""
        task = await create_task(authed_client)

        # Post a comment mentioning @Executor
        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "Hey @Executor can you help with this?"},
        )
        assert resp.status_code == 201

        # Fetch comments: AI auto-comments + user comment + agent reply
        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        assert resp.status_code == 200
        comments = resp.json()

        # Top-level: 2 AI auto-comments + user comment with mention
        assert len(comments) == 3

        user_comment = next(c for c in comments if c["content"] == "Hey @Executor can you help with this?")
        # The agent reply should be nested under the user comment
        assert len(user_comment["replies"]) == 1
        reply = user_comment["replies"][0]
        assert reply["author_type"] == "agent"
        assert reply["author_name"] == "Executor"
        assert "Task Summary" in reply["content"]
        assert task["title"] in reply["content"]

    async def test_post_response_and_background_reply(self, authed_client: AsyncClient):
        """The agent reply is created in the background; a GET should return it."""
        task = await create_task(authed_client)

        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "Hey @Executor summarise this"},
        )
        assert resp.status_code == 201
        comment = resp.json()

        # POST response returns before the background task finishes
        # so replies may be empty here — that's fine.

        # Fetch via GET — the background task has completed by the time
        # the ASGI transport returns the POST above, so the reply should exist.
        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()
        user_comment = next(c for c in comments if c["id"] == comment["id"])
        assert len(user_comment["replies"]) == 1
        reply = user_comment["replies"][0]
        assert reply["author_type"] == "agent"
        assert reply["author_name"] == "Executor"
        assert "Task Summary" in reply["content"]

    async def test_mention_thinker_triggers_reply(self, authed_client: AsyncClient):
        """Mentioning @Thinker in a comment should produce a Thinker agent reply."""
        task = await create_task(authed_client)

        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Thinker what do you think about this task?"},
        )
        assert resp.status_code == 201

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        user_comment = next(c for c in comments if "@Thinker" in c["content"])
        assert len(user_comment["replies"]) == 1
        reply = user_comment["replies"][0]
        assert reply["author_name"] == "Thinker"
        assert "Task Summary" in reply["content"]

    async def test_mention_multiple_agents(self, authed_client: AsyncClient):
        """Mentioning both @Executor and @Thinker should produce two replies."""
        task = await create_task(authed_client)

        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Executor and @Thinker please review this."},
        )
        assert resp.status_code == 201

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        user_comment = next(c for c in comments if "@Executor" in c["content"])
        assert len(user_comment["replies"]) == 2
        reply_names = {r["author_name"] for r in user_comment["replies"]}
        assert reply_names == {"Executor", "Thinker"}

    async def test_no_mention_no_reply(self, authed_client: AsyncClient):
        """A comment without @mentions should not produce any agent reply."""
        task = await create_task(authed_client)

        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "Just a regular comment"},
        )
        assert resp.status_code == 201

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        user_comment = next(c for c in comments if c["content"] == "Just a regular comment")
        assert len(user_comment["replies"]) == 0

    async def test_mention_invalid_agent_no_reply(self, authed_client: AsyncClient):
        """Mentioning a non-existent agent name should not produce a reply."""
        task = await create_task(authed_client)

        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@NonExistentBot help me"},
        )
        assert resp.status_code == 201

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        user_comment = next(c for c in comments if "@NonExistentBot" in c["content"])
        assert len(user_comment["replies"]) == 0

    async def test_reply_contains_task_summary(self, authed_client: AsyncClient):
        """The agent reply should contain a summary with task details."""
        task = await create_task(
            authed_client,
            title="Fix the API bug",
            description="The /api/tasks endpoint returns 500",
            priority="high",
            status="in_progress",
        )

        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Executor please fix this ASAP"},
        )
        assert resp.status_code == 201

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        user_comment = next(c for c in comments if "@Executor" in c["content"])
        reply = user_comment["replies"][0]

        # Check that the reply references task details
        assert "Fix the API bug" in reply["content"]
        assert "high" in reply["content"]
        assert "in_progress" in reply["content"]

    async def test_reply_quotes_user_comment(self, authed_client: AsyncClient):
        """The agent reply should quote the original user comment."""
        task = await create_task(authed_client)

        user_text = "@Thinker can you analyse the dependencies?"
        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": user_text},
        )
        assert resp.status_code == 201

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        user_comment = next(c for c in comments if "@Thinker" in c["content"])
        reply = user_comment["replies"][0]

        # The reply should contain the quoted comment text
        assert "Your comment" in reply["content"]
        assert "analyse the dependencies" in reply["content"]

    async def test_reply_is_child_of_original_comment(self, authed_client: AsyncClient):
        """The agent reply should have parent_id pointing to the original comment."""
        task = await create_task(authed_client)

        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Executor check this"},
        )
        assert resp.status_code == 201
        original_comment = resp.json()

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        user_comment = next(c for c in comments if c["id"] == original_comment["id"])
        reply = user_comment["replies"][0]
        assert reply["parent_id"] == original_comment["id"]

    async def test_duplicate_mention_only_one_reply(self, authed_client: AsyncClient):
        """Mentioning the same agent twice should produce only one reply."""
        task = await create_task(authed_client)

        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "@Executor do this, @Executor please"},
        )
        assert resp.status_code == 201

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()

        user_comment = next(c for c in comments if "@Executor" in c["content"])
        assert len(user_comment["replies"]) == 1

    async def test_mention_skipped_when_agent_missing(self):
        """When the mentioned agent is not in the DB, no reply is created."""
        from app.ai.agent_mention import handle_agent_mentions
        from tests.conftest import TestSession

        # Delete all agents
        async with TestSession() as db:
            await db.execute(delete(Agent))
            await db.commit()

        # Should not raise
        await handle_agent_mentions(
            task_id=str(uuid.uuid4()),
            comment_id=str(uuid.uuid4()),
            comment_content="@Executor help me",
        )
        # No crash = success


@pytest.mark.anyio
class TestExtractMentionedNames:
    def test_single_mention(self):
        from app.ai.agent_mention import extract_mentioned_agent_names

        assert extract_mentioned_agent_names("Hello @Executor") == ["Executor"]

    def test_multiple_mentions(self):
        from app.ai.agent_mention import extract_mentioned_agent_names

        result = extract_mentioned_agent_names("@Executor and @Thinker")
        assert result == ["Executor", "Thinker"]

    def test_no_mentions(self):
        from app.ai.agent_mention import extract_mentioned_agent_names

        assert extract_mentioned_agent_names("no mentions here") == []

    def test_duplicate_mentions(self):
        from app.ai.agent_mention import extract_mentioned_agent_names

        result = extract_mentioned_agent_names("@Executor then @Executor again")
        assert result == ["Executor"]

    def test_mention_at_start(self):
        from app.ai.agent_mention import extract_mentioned_agent_names

        assert extract_mentioned_agent_names("@Thinker what do you think?") == ["Thinker"]


@pytest.mark.anyio
class TestBuildMentionLlm:
    """Tests for _build_llm in agent_mention module."""

    async def test_build_llm_mock_provider(self):
        """When LLM_PROVIDER is 'mock', _build_llm returns MockMentionLLM."""
        from unittest.mock import patch

        from app.ai.agent_mention import MockMentionLLM, _build_llm

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "mock"
            llm = _build_llm()
        assert isinstance(llm, MockMentionLLM)

    async def test_get_mention_llm_lazy_init(self):
        """_get_mention_llm calls _build_llm when _mention_llm is None."""
        from unittest.mock import patch

        from app.ai.agent_mention import (
            MockMentionLLM,
            _get_mention_llm,
            set_mention_llm,
        )

        # Reset to None so lazy init triggers
        set_mention_llm(None)
        try:
            with patch("app.core.config.settings") as mock_settings:
                mock_settings.LLM_PROVIDER = "mock"
                llm = _get_mention_llm()
            assert isinstance(llm, MockMentionLLM)
        finally:
            # Restore mock LLM for other tests
            set_mention_llm(MockMentionLLM())

    async def test_build_llm_ollama_success(self):
        """When LLM_PROVIDER is 'ollama' and ChatOllama works, returns ChatOllama."""
        from unittest.mock import MagicMock, patch

        from app.ai.agent_mention import _build_llm

        mock_ollama_cls = MagicMock()
        mock_ollama_instance = MagicMock()
        mock_ollama_cls.return_value = mock_ollama_instance

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "ollama"
            mock_settings.OLLAMA_MODEL = "llama3"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            with patch.dict(
                "sys.modules",
                {"langchain_ollama": MagicMock(ChatOllama=mock_ollama_cls)},
            ):
                llm = _build_llm()
        assert llm is mock_ollama_instance

    async def test_build_llm_ollama_failure_fallback(self):
        """When LLM_PROVIDER is 'ollama' but import fails, falls back to MockMentionLLM."""
        from unittest.mock import patch

        from app.ai.agent_mention import MockMentionLLM, _build_llm

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "ollama"
            mock_settings.OLLAMA_MODEL = "llama3"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            # Remove langchain_ollama from sys.modules to force ImportError
            with patch.dict("sys.modules", {"langchain_ollama": None}):
                llm = _build_llm()
        assert isinstance(llm, MockMentionLLM)


@pytest.mark.anyio
class TestBuildMentionPrompt:
    """Direct tests for build_mention_prompt and call_mention_llm."""

    async def test_build_mention_prompt_directly(self):
        """build_mention_prompt returns state with populated result prompt."""
        from app.ai.agent_mention import build_mention_prompt

        state = {
            "agent_name": "Executor",
            "task_title": "Fix bug",
            "task_description": "There is a bug in login",
            "task_priority": "high",
            "task_status": "in_progress",
            "comment_content": "@Executor please look at this",
            "result": "",
        }
        out = build_mention_prompt(state)
        assert "Executor" in out["result"]
        assert "Fix bug" in out["result"]
        assert "There is a bug in login" in out["result"]
        assert "high" in out["result"]
        assert "in_progress" in out["result"]
        assert "@Executor please look at this" in out["result"]

    async def test_build_mention_prompt_no_description(self):
        """build_mention_prompt shows '(none)' when description is empty."""
        from app.ai.agent_mention import build_mention_prompt

        state = {
            "agent_name": "Thinker",
            "task_title": "Task",
            "task_description": "",
            "task_priority": "low",
            "task_status": "todo",
            "comment_content": "@Thinker help",
            "result": "",
        }
        out = build_mention_prompt(state)
        assert "(none)" in out["result"]

    async def test_call_mention_llm_directly(self):
        """call_mention_llm invokes the LLM and stores response in result."""
        from app.ai.agent_mention import (
            MockMentionLLM,
            call_mention_llm,
            set_mention_llm,
        )

        set_mention_llm(MockMentionLLM())
        state = {
            "agent_name": "Executor",
            "task_title": "Fix bug",
            "task_description": "Bug in login",
            "task_priority": "high",
            "task_status": "in_progress",
            "comment_content": "@Executor help",
            "result": (
                "You are **Executor**\n\n"
                "Title: Fix bug\n"
                "Description: Bug in login\n"
                "Priority: high\n"
                "Status: in_progress\n\n"
                "--- User comment ---\n"
                "@Executor help\n\n"
                "Respond in Markdown."
            ),
        }
        out = await call_mention_llm(state)
        assert "Task Summary" in out["result"]
        assert "Fix bug" in out["result"]
