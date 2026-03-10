"""Tests for the browser tool and ReAct agent integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PLAYWRIGHT_PATCH = "playwright.async_api.async_playwright"


def _make_mock_playwright(page_text: str = "Hello World"):
    """Build a full mock Playwright stack returning *page_text*."""
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.inner_text = AsyncMock(return_value=page_text)

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


@pytest.mark.anyio
class TestBrowseWebpage:
    """Tests for the browse_webpage tool."""

    async def test_browse_returns_page_text(self):
        """browse_webpage should return the visible text of the page."""
        from app.ai.tools.browser import browse_webpage

        mock = _make_mock_playwright("FlixBus: Bratislava to Berlin €19")
        with patch(PLAYWRIGHT_PATCH, return_value=mock):
            result = await browse_webpage.ainvoke({"url": "https://www.flixbus.com"})

        assert "FlixBus" in result
        assert "€19" in result

    async def test_browse_truncates_long_content(self):
        """browse_webpage should truncate very long page text."""
        from app.ai.tools.browser import _MAX_CONTENT_LENGTH, browse_webpage

        long_text = "A" * (_MAX_CONTENT_LENGTH + 5000)
        with patch(PLAYWRIGHT_PATCH, return_value=_make_mock_playwright(long_text)):
            result = await browse_webpage.ainvoke({"url": "https://example.com"})

        assert result.endswith("…(truncated)")
        assert len(result) <= _MAX_CONTENT_LENGTH + len("\n…(truncated)")

    async def test_browse_handles_error_gracefully(self):
        """browse_webpage should return an error message on failure."""
        from app.ai.tools.browser import browse_webpage

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with patch(PLAYWRIGHT_PATCH, return_value=mock_cm):
            result = await browse_webpage.ainvoke({"url": "https://down.example.com"})

        assert "Error browsing" in result
        assert "Connection refused" in result


@pytest.mark.anyio
class TestReActAgentPath:
    """Test the ReAct agent path in call_mention_llm (non-mock LLM)."""

    async def test_call_mention_llm_react_path(self):
        """When a non-mock LLM is set, call_mention_llm uses the ReAct agent."""
        from langchain_core.messages import AIMessage

        from app.ai.agent_mention import (
            MockMentionLLM,
            call_mention_llm,
            set_mention_llm,
        )

        # Create a fake LLM that is NOT MockMentionLLM so we take the ReAct path.
        mock_react_agent = AsyncMock()
        mock_react_agent.ainvoke = AsyncMock(
            return_value={"messages": [AIMessage(content="The cheapest ticket is €19.")]}
        )

        fake_llm = MagicMock()  # Not a MockMentionLLM instance

        try:
            set_mention_llm(fake_llm)

            with patch(
                "langgraph.prebuilt.create_react_agent",
                return_value=mock_react_agent,
            ) as mock_create:
                state = {
                    "agent_name": "Executor",
                    "task_title": "Travel",
                    "task_description": "Find bus tickets",
                    "task_priority": "medium",
                    "task_status": "in_progress",
                    "comment_content": "What is the cheapest bus?",
                    "result": "You are Executor...",
                }
                out = await call_mention_llm(state)

            assert out["result"] == "The cheapest ticket is €19."
            mock_create.assert_called_once()
            mock_react_agent.ainvoke.assert_called_once()
        finally:
            # Restore mock LLM for other tests
            set_mention_llm(MockMentionLLM())
