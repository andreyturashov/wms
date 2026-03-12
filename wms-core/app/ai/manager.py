"""
Manager agent pipeline.

The Manager is a meta-agent that reviews conversations and adjusts other
agents' system prompts to better fit the discussion context.  It runs
automatically after agent interactions, making subtle refinements so
Executor / Thinker stay effective and relevant.
"""

from __future__ import annotations

import logging
import re
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, StateGraph
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.comment import Comment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel returned by the LLM when no prompt change is needed
# ---------------------------------------------------------------------------

PROMPT_UNCHANGED = "PROMPT_UNCHANGED"

# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------


class MockManagerLLM(BaseChatModel):
    """Deterministic mock for tests — always returns a small prompt tweak."""

    model_name: str = "mock-manager"

    @property
    def _llm_type(self) -> str:
        return "mock-manager"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs,
    ) -> ChatResult:
        prompt_text = messages[-1].content if messages else ""

        # Extract the current system prompt from the structured input
        marker = "Current system prompt:\n"
        if marker in prompt_text:
            after = prompt_text.split(marker, 1)[1]
            current = after.split("\n\nRecent conversation:", 1)[0]
        else:
            current = ""

        # Deterministic tweak: append a context-awareness line
        updated = current.rstrip() + "\n\nStay aware of the ongoing discussion context and adapt your tone accordingly."
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=updated))])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs,
    ) -> ChatResult:
        return self._generate(messages, stop, **kwargs)


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

_manager_llm: BaseChatModel | None = None


def _build_manager_llm() -> BaseChatModel:
    from app.core.config import settings

    provider = settings.LLM_PROVIDER.lower()
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama

            logger.info("Manager: using Ollama LLM (model=%s)", settings.OLLAMA_MODEL)
            return ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
            )
        except Exception:
            logger.warning("Manager: Ollama init failed, falling back to mock")
            return MockManagerLLM()
    return MockManagerLLM()


def _get_manager_llm() -> BaseChatModel:
    global _manager_llm
    if _manager_llm is None:
        _manager_llm = _build_manager_llm()
    return _manager_llm


def set_manager_llm(llm: BaseChatModel | None) -> None:
    """Override the Manager LLM instance (used by tests)."""
    global _manager_llm
    _manager_llm = llm


# ---------------------------------------------------------------------------
# LangGraph state & nodes
# ---------------------------------------------------------------------------


class ManagerReviewState(TypedDict):
    agent_key: str
    current_prompt: str
    conversation_context: str
    system_prompt: str  # Manager's own persona
    result: str


def build_review_prompt(state: ManagerReviewState) -> ManagerReviewState:
    """Build the prompt asking the LLM to review/adjust an agent's system prompt."""
    manager_persona = state.get("system_prompt") or ""
    persona_block = f"{manager_persona}\n\n" if manager_persona else ""

    prompt = (
        f"{persona_block}"
        f"You are the **Manager Agent** in a project-management system.\n\n"
        f"Your task is to review a conversation and decide whether a fellow "
        f"agent's system prompt needs a subtle adjustment to be more effective.\n\n"
        f"Agent being reviewed: **{state['agent_key']}**\n\n"
        f"Current system prompt:\n{state['current_prompt']}\n\n"
        f"Recent conversation:\n{state['conversation_context']}\n\n"
        f"Instructions:\n"
        f"- If the agent's responses could benefit from a small prompt tweak, "
        f"return the complete updated system prompt.\n"
        f"- Make only subtle, targeted changes — do NOT rewrite the whole prompt.\n"
        f"- Preserve the agent's core personality and style.\n"
        f"- If no changes are needed, return exactly: {PROMPT_UNCHANGED}"
    )
    return {**state, "result": prompt}


async def call_manager_llm(state: ManagerReviewState) -> ManagerReviewState:
    """Invoke the Manager LLM and store the response."""
    llm = _get_manager_llm()
    response = await llm.ainvoke([HumanMessage(content=state["result"])])
    return {**state, "result": response.content}


# Build the graph
_manager_graph_builder = StateGraph(ManagerReviewState)
_manager_graph_builder.add_node("build_prompt", build_review_prompt)
_manager_graph_builder.add_node("call_llm", call_manager_llm)
_manager_graph_builder.set_entry_point("build_prompt")
_manager_graph_builder.add_edge("build_prompt", "call_llm")
_manager_graph_builder.add_edge("call_llm", END)

manager_review_graph = _manager_graph_builder.compile()

# ---------------------------------------------------------------------------
# Pluggable session factory
# ---------------------------------------------------------------------------

_session_factory = AsyncSessionLocal


def set_session_factory(factory) -> None:
    """Override the async session factory (used by tests)."""
    global _session_factory
    _session_factory = factory


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def review_and_adjust(task_id: str, agent_key: str) -> str | None:
    """
    Review recent conversation on a task and adjust the specified agent's
    system prompt if the Manager deems it beneficial.

    Returns the new prompt if updated, or ``None`` if unchanged.
    """
    async with _session_factory() as db:
        # Load the target agent
        agent_result = await db.execute(select(Agent).where(Agent.key == agent_key, Agent.is_active.is_(True)))
        agent = agent_result.scalar_one_or_none()
        if not agent:
            logger.warning("Manager: agent '%s' not found — skipping review", agent_key)
            return None

        # Load the Manager agent for its persona
        manager_result = await db.execute(select(Agent).where(Agent.key == "manager"))
        manager_agent = manager_result.scalar_one_or_none()
        manager_prompt = manager_agent.system_prompt if manager_agent else ""

        # Load recent comments on this task (last 20, chronological)
        comments_result = await db.execute(
            select(Comment).where(Comment.task_id == task_id).order_by(Comment.created_at.desc()).limit(20)
        )
        comments = comments_result.scalars().all()

        if not comments:
            return None

        # Map agent IDs to keys for labeling
        agents_result = await db.execute(select(Agent))
        agents_map = {a.id: a.key for a in agents_result.scalars().all()}

        # Build conversation context (chronological)
        lines = []
        for c in reversed(comments):
            author = agents_map.get(c.agent_id, "agent") if c.agent_id else "user"
            lines.append(f"{author}: {c.content}")
        conversation_context = "\n".join(lines)

        current_prompt = agent.system_prompt or ""

    # Run the Manager LangGraph pipeline
    result = await manager_review_graph.ainvoke(
        {
            "agent_key": agent_key,
            "current_prompt": current_prompt,
            "conversation_context": conversation_context,
            "system_prompt": manager_prompt,
            "result": "",
        }
    )

    new_prompt = result["result"].strip()

    if new_prompt == PROMPT_UNCHANGED or not new_prompt:
        logger.info("Manager: no prompt changes for agent '%s'", agent_key)
        return None

    # Persist the updated system prompt
    async with _session_factory() as db:
        agent_result = await db.execute(select(Agent).where(Agent.key == agent_key))
        agent = agent_result.scalar_one_or_none()
        if agent:
            agent.system_prompt = new_prompt
            await db.commit()
            logger.info("Manager: updated system prompt for agent '%s'", agent_key)
            return new_prompt

    return None


# ---------------------------------------------------------------------------
# Skill-addition via @Manager
# ---------------------------------------------------------------------------

# Matches: "add skill to @Agent ... that <skill description>"
_SKILL_RE = re.compile(
    r"add\s+skill\s+to\s+@(\w+)(?:\s+\w+)?\s+that\s+(.+)",
    re.IGNORECASE,
)


def parse_skill_request(content: str) -> tuple[str, str] | None:
    """
    Parse a "add skill to @Agent that <skill>" instruction.

    Returns ``(agent_key, skill_text)`` or ``None`` if the content doesn't
    match the pattern.
    """
    m = _SKILL_RE.search(content)
    if not m:
        return None
    agent_key = m.group(1).strip()
    skill_text = m.group(2).strip().rstrip(".")
    if not skill_text:
        return None
    return agent_key, skill_text


async def add_skill_to_agent(agent_key: str, skill_text: str) -> str | None:
    """
    Append a skill line to the target agent's system prompt.

    Returns the updated prompt, or ``None`` if the agent was not found.
    """
    async with _session_factory() as db:
        agent_result = await db.execute(select(Agent).where(Agent.key == agent_key.lower(), Agent.is_active.is_(True)))
        agent = agent_result.scalar_one_or_none()
        if not agent:
            logger.warning("Manager: cannot add skill — agent '%s' not found", agent_key)
            return None

        current = (agent.system_prompt or "").rstrip()
        skill_line = f"- Remember: {skill_text}"

        if skill_line in current:
            logger.info("Manager: skill already present for '%s'", agent_key)
            return current

        agent.system_prompt = f"{current}\n\n{skill_line}" if current else skill_line
        await db.commit()
        logger.info("Manager: added skill to agent '%s': %s", agent_key, skill_text)
        return agent.system_prompt
