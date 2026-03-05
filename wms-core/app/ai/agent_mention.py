"""
Agent mention reaction pipeline.

When a user posts a comment that mentions an agent (e.g. ``@Executor`` or
``@Thinker``), this module detects the mention, summarises the task, quotes the
comment, and posts a reply authored by the mentioned agent.

The LLM backend is configurable via ``settings.LLM_PROVIDER``:
- ``"ollama"`` – calls a local Ollama instance (default).
- ``"mock"``  – deterministic mock for tests / offline work.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, StateGraph
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.comment import Comment
from app.models.task import Task

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock LLM (used in tests and when LLM_PROVIDER="mock")
# ---------------------------------------------------------------------------


class MockMentionLLM(BaseChatModel):
    """Fake chat model that returns a canned task summary + quoted comment."""

    model_name: str = "mock-mention"

    @property
    def _llm_type(self) -> str:
        return "mock-mention"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs,
    ) -> ChatResult:
        prompt_text = messages[-1].content if messages else ""

        # Parse structured fields out of the prompt
        lines = prompt_text.split("\n")
        task_title = ""
        task_desc = ""
        task_priority = ""
        task_status = ""
        comment_text = ""

        in_comment = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Title:"):
                task_title = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Description:"):
                task_desc = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Priority:"):
                task_priority = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Status:"):
                task_status = stripped.split(":", 1)[1].strip()
            elif stripped == "--- User comment ---":
                in_comment = True
            elif in_comment and stripped and not stripped.startswith("Respond in Markdown"):
                comment_text += ("\n" if comment_text else "") + line

        comment_text = comment_text.strip()

        response = (
            f"**Task Summary**\n\n"
            f"• **Title**: {task_title}\n"
            f"• **Description**: {task_desc or '(none)'}\n"
            f"• **Priority**: {task_priority}\n"
            f"• **Status**: {task_status}\n\n"
            f"**Your comment**:\n"
            f"> {comment_text}\n\n"
            f"I've reviewed the task and the comment. "
            f"The task is currently **{task_status}** with **{task_priority}** priority. "
            f"Let me know if you need further assistance."
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response))])


# ---------------------------------------------------------------------------
# LLM factory – returns Ollama or Mock depending on settings
# ---------------------------------------------------------------------------


def _build_llm() -> BaseChatModel:
    """Return the configured LLM instance (Ollama or Mock)."""
    from app.core.config import settings

    provider = settings.LLM_PROVIDER.lower()
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama

            logger.info(
                "Using Ollama LLM (model=%s, base_url=%s)",
                settings.OLLAMA_MODEL,
                settings.OLLAMA_BASE_URL,
            )
            return ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
            )
        except Exception:
            logger.warning("Failed to initialise Ollama. Falling back to MockMentionLLM")
            return MockMentionLLM()
    else:
        return MockMentionLLM()


# ---------------------------------------------------------------------------
# LangGraph state & nodes
# ---------------------------------------------------------------------------


class MentionReactionState(TypedDict):
    """State that flows through the mention-reaction graph."""

    agent_name: str
    task_title: str
    task_description: str
    task_priority: str
    task_status: str
    comment_content: str
    result: str


def build_mention_prompt(state: MentionReactionState) -> MentionReactionState:
    """Build the prompt for the mention-reaction LLM call (node 1)."""
    prompt = (
        f"You are **{state['agent_name']}**, an AI agent embedded in a "
        f"project-management system.\n\n"
        f"A team member mentioned you in a comment on a task. Your job is to:\n"
        f"1. Briefly summarise the task.\n"
        f"2. Answer or address the user's comment / question.\n"
        f"3. Offer actionable suggestions if appropriate.\n\n"
        f"--- Task details ---\n"
        f"Title: {state['task_title']}\n"
        f"Description: {state['task_description'] or '(none)'}\n"
        f"Priority: {state['task_priority']}\n"
        f"Status: {state['task_status']}\n\n"
        f"--- User comment ---\n"
        f"{state['comment_content']}\n\n"
        f"Respond in Markdown. Be concise but helpful."
    )
    return {**state, "result": prompt}


# The LLM instance is created lazily so tests can override LLM_PROVIDER="mock".
_mention_llm: BaseChatModel | None = None


def _get_mention_llm() -> BaseChatModel:
    global _mention_llm
    if _mention_llm is None:
        _mention_llm = _build_llm()
    return _mention_llm


def set_mention_llm(llm: BaseChatModel | None) -> None:
    """Replace the mention LLM instance (used by tests)."""
    global _mention_llm
    _mention_llm = llm


def call_mention_llm(state: MentionReactionState) -> MentionReactionState:
    """Invoke the LLM and store the response (node 2)."""
    from langchain_core.messages import HumanMessage

    llm = _get_mention_llm()
    response = llm.invoke([HumanMessage(content=state["result"])])
    return {**state, "result": response.content}


# Build the graph
_mention_graph_builder = StateGraph(MentionReactionState)
_mention_graph_builder.add_node("build_prompt", build_mention_prompt)
_mention_graph_builder.add_node("call_llm", call_mention_llm)
_mention_graph_builder.set_entry_point("build_prompt")
_mention_graph_builder.add_edge("build_prompt", "call_llm")
_mention_graph_builder.add_edge("call_llm", END)

mention_reaction_graph = _mention_graph_builder.compile()


# ---------------------------------------------------------------------------
# Detection helper
# ---------------------------------------------------------------------------

# Matches @AgentName patterns (e.g. "@Executor", "@Thinker")
_MENTION_RE = re.compile(r"@(\w+)")


def extract_mentioned_agent_names(content: str) -> list[str]:
    """Return a list of unique mentioned names from the comment content."""
    return list(dict.fromkeys(_MENTION_RE.findall(content)))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Pluggable session factory – overridden by tests
_session_factory = AsyncSessionLocal


def set_session_factory(factory) -> None:
    """Override the async session factory (used by tests)."""
    global _session_factory
    _session_factory = factory


async def handle_agent_mentions(
    task_id: str,
    comment_id: str,
    comment_content: str,
) -> None:
    """
    Detect @Agent mentions in *comment_content*, and for each matched agent
    post a reply summarising the task and quoting the comment.
    """
    mentioned_names = extract_mentioned_agent_names(comment_content)
    if not mentioned_names:
        return

    async with _session_factory() as db:
        # Load the task
        task_result = await db.execute(select(Task).where(Task.id == task_id))
        task = task_result.scalar_one_or_none()
        if not task:
            return

        # Load all active agents and match by key (case-insensitive).
        # The regex captures a single word after '@', so we match against the
        # agent's `key` field (e.g. "executor", "thinker") rather than the
        # multi-word `name` (e.g. "Executor Agent").
        agents_result = await db.execute(select(Agent).where(Agent.is_active.is_(True)))
        all_agents = agents_result.scalars().all()
        key_to_agent = {a.key.lower(): a for a in all_agents}

        for mentioned_name in mentioned_names:
            agent = key_to_agent.get(mentioned_name.lower())
            if not agent:
                continue  # not a valid agent key – skip

            # Run the LangGraph pipeline
            result = mention_reaction_graph.invoke(
                {
                    "agent_name": agent.name,
                    "task_title": task.title,
                    "task_description": task.description or "",
                    "task_priority": task.priority,
                    "task_status": task.status,
                    "comment_content": comment_content,
                    "result": "",
                }
            )

            reply = Comment(
                id=str(uuid.uuid4()),
                task_id=task_id,
                content=result["result"],
                user_id=None,
                agent_id=agent.id,
                parent_id=comment_id,
            )
            db.add(reply)

        await db.commit()
