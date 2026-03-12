"""
LangGraph-based task analysis pipeline.

When a new task is created the graph analyses it and produces structured
comments from each registered AI agent (Executor and Thinker).

Each agent has a ``Professional.md`` that defines its persona and output
format.  The file is loaded at runtime and injected as the LLM system prompt
so every agent behaves according to its own specification.

For now the LLM call is **mocked** - it returns a deterministic result built
from the task data so the feature can be developed and tested without an API
key.  Replace ``MockLLM`` with a real chat model to go live.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, StateGraph
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.comment import Comment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent keys for the two active agents
# ---------------------------------------------------------------------------

AGENT_KEYS: list[str] = ["executor", "thinker"]

# Directory that holds per-agent Professional.md files
_AGENTS_DIR = Path(__file__).resolve().parent / "agents"


def load_professional_md(agent_key: str) -> str:
    """Return the contents of ``agents/<key>/Professional.md``, or empty."""
    md_path = _AGENTS_DIR / agent_key / "Professional.md"
    if md_path.is_file():
        return md_path.read_text(encoding="utf-8")
    logger.warning("Professional.md not found for agent '%s' at %s", agent_key, md_path)
    return ""


# ---------------------------------------------------------------------------
# Mock LLM - replace with a real model later
# ---------------------------------------------------------------------------


class MockLLM(BaseChatModel):
    """A fake chat model that returns a canned analysis of the task."""

    model_name: str = "mock"

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs,
    ) -> ChatResult:
        # Detect agent type from the system message (if present)
        system_text = ""
        for m in messages:
            if isinstance(m, SystemMessage):
                system_text = str(m.content)
                break

        if "# Executor Agent" in system_text:
            response = (
                "Looks straightforward — I'd tackle this directly with "
                "incremental changes and good test coverage. The existing "
                "codebase should support it without major refactoring."
            )
        elif "# Thinker Agent" in system_text:
            response = (
                "This is pretty clear-cut, but worth considering: a direct "
                "implementation is fast and low-risk, though a broader refactor "
                "could pay off long-term. Keep an eye on edge cases and "
                "backwards compatibility."
            )
        else:
            response = (
                "I've reviewed the task — it looks well-scoped, probably small "
                "to medium effort. If it grows, consider breaking it into "
                "subtasks. No obvious dependencies."
            )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response))])


# ---------------------------------------------------------------------------
# LLM factory / injection
# ---------------------------------------------------------------------------


def _build_llm() -> BaseChatModel:
    """Build the LLM instance based on ``settings.LLM_PROVIDER``."""
    provider = getattr(settings, "LLM_PROVIDER", "mock")

    if provider == "ollama":  # pragma: no cover
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )

    if provider != "mock":
        logger.warning("Unknown LLM_PROVIDER '%s' - falling back to MockLLM", provider)

    return MockLLM()


_llm: BaseChatModel = _build_llm()


def set_llm(llm: BaseChatModel) -> None:
    """Override the active LLM instance (used by tests)."""
    global _llm
    _llm = llm


def _get_llm() -> BaseChatModel:
    return _llm


# ---------------------------------------------------------------------------
# LangGraph state & nodes
# ---------------------------------------------------------------------------


class TaskAnalysisState(TypedDict):
    """State that flows through the graph."""

    task_title: str
    task_description: str
    task_priority: str
    task_status: str
    system_prompt: str  # Professional.md content
    result: str  # LLM output


def build_prompt(state: TaskAnalysisState) -> TaskAnalysisState:
    """Prepare the LLM prompt from the task data (node 1)."""
    prompt = (
        f"A new task has been created in the project-management system.\n\n"
        f"Title: {state['task_title']}\n"
        f"Description: {state['task_description'] or '(none)'}\n"
        f"Priority: {state['task_priority']}\n"
        f"Status: {state['task_status']}\n\n"
        f"Provide a direct, substantive response to this task. "
        f"Do not describe how you would approach it - deliver the actual result."
    )
    return {**state, "result": prompt}


def call_llm(state: TaskAnalysisState) -> TaskAnalysisState:
    """Invoke the LLM with a system prompt and store the response (node 2)."""
    messages: list[BaseMessage] = []
    if state.get("system_prompt"):
        messages.append(SystemMessage(content=state["system_prompt"]))
    messages.append(HumanMessage(content=state["result"]))

    response = _get_llm().invoke(messages)
    return {**state, "result": response.content}


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

_graph_builder = StateGraph(TaskAnalysisState)
_graph_builder.add_node("build_prompt", build_prompt)
_graph_builder.add_node("call_llm", call_llm)
_graph_builder.set_entry_point("build_prompt")
_graph_builder.add_edge("build_prompt", "call_llm")
_graph_builder.add_edge("call_llm", END)

task_analysis_graph = _graph_builder.compile()


# ---------------------------------------------------------------------------
# Public helper - run the graph and persist the result as a comment
# ---------------------------------------------------------------------------

ASSISTANT_AGENT_KEY = "thinker"

# Pluggable session factory – overridden by tests via set_session_factory()
_session_factory = AsyncSessionLocal


def set_session_factory(factory) -> None:
    """Override the async session factory (used by tests)."""
    global _session_factory
    _session_factory = factory


async def analyse_task_and_comment(
    task_id: str,
    title: str,
    description: str,
    priority: str,
    task_status: str,
) -> None:
    """Run the LangGraph pipeline for every active agent and save comments."""

    for agent_key in AGENT_KEYS:
        logger.info("Running AI analysis for agent '%s' on task %s", agent_key, task_id)

        # Prefer DB system_prompt, fall back to file
        async with _session_factory() as db:
            agent = (await db.execute(select(Agent).where(Agent.key == agent_key))).scalar_one_or_none()

        if not agent:
            logger.warning("Agent '%s' not found in DB - skipping comment", agent_key)
            continue

        system_prompt = agent.system_prompt or load_professional_md(agent_key)

        try:
            result = await asyncio.to_thread(
                task_analysis_graph.invoke,
                {
                    "task_title": title,
                    "task_description": description,
                    "task_priority": priority,
                    "task_status": task_status,
                    "system_prompt": system_prompt,
                    "result": "",
                },
            )
        except Exception:
            logger.exception("Graph execution failed for agent '%s'", agent_key)
            continue

        ai_content: str = result["result"]
        logger.info("Agent '%s' analysis length: %d chars", agent_key, len(ai_content))

        async with _session_factory() as db:
            comment = Comment(
                id=str(uuid.uuid4()),
                task_id=task_id,
                content=ai_content,
                user_id=None,
                agent_id=agent.id,
                parent_id=None,
            )
            db.add(comment)
            await db.commit()

        logger.info("Saved comment from agent '%s' for task %s", agent_key, task_id)
