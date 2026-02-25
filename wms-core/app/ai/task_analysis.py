"""
LangGraph-based task analysis pipeline.

When a new task is created the graph analyses it and produces a structured
recommendation that is stored as a comment authored by the Assistant Agent.

For now the LLM call is **mocked** – it returns a deterministic result built
from the task data so the feature can be developed and tested without an API
key.  Replace `MockLLM` with a real chat model (e.g. `ChatOpenAI`) to go live.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, StateGraph

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.agent import Agent
from app.models.comment import Comment


# ---------------------------------------------------------------------------
# Mock LLM – replace with a real model later
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
        # Extract task info from the last human message
        prompt_text = messages[-1].content if messages else ""
        response = (
            f"**AI Analysis**\n\n"
            f"I've reviewed the new task. Here are my recommendations:\n\n"
            f"• **Priority assessment**: The described work appears well-scoped.\n"
            f"• **Estimated effort**: Small to medium.\n"
            f"• **Suggested next steps**: Break the task into subtasks if it "
            f"grows beyond a single session.\n"
            f"• **Dependencies**: None detected.\n\n"
            f"_This analysis was generated automatically when the task was created._"
        )
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=response))]
        )


# ---------------------------------------------------------------------------
# LangGraph state & nodes
# ---------------------------------------------------------------------------


class TaskAnalysisState(TypedDict):
    """State that flows through the graph."""

    task_title: str
    task_description: str
    task_priority: str
    task_status: str
    result: str  # LLM output


def build_prompt(state: TaskAnalysisState) -> TaskAnalysisState:
    """Prepare the LLM prompt from the task data (node 1)."""
    # We encode the prompt into `result` temporarily; the next node will
    # overwrite it with the LLM response.
    prompt = (
        f"A new task has been created in the project-management system.\n\n"
        f"Title: {state['task_title']}\n"
        f"Description: {state['task_description'] or '(none)'}\n"
        f"Priority: {state['task_priority']}\n"
        f"Status: {state['task_status']}\n\n"
        f"Please analyse this task and provide recommendations on priority, "
        f"estimated effort, suggested next steps, and potential dependencies."
    )
    return {**state, "result": prompt}


_llm = MockLLM()


def call_llm(state: TaskAnalysisState) -> TaskAnalysisState:
    """Invoke the (mock) LLM and store the response (node 2)."""
    from langchain_core.messages import HumanMessage

    response = _llm.invoke([HumanMessage(content=state["result"])])
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
# Public helper – run the graph and persist the result as a comment
# ---------------------------------------------------------------------------

ASSISTANT_AGENT_KEY = "assistant"

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
    """Run the LangGraph pipeline and save the output as an agent comment."""

    # 1. Execute the graph (sync under the hood – mock is instant)
    result = task_analysis_graph.invoke(
        {
            "task_title": title,
            "task_description": description,
            "task_priority": priority,
            "task_status": task_status,
            "result": "",
        }
    )

    ai_content: str = result["result"]

    # 2. Persist as a comment authored by the Assistant Agent
    async with _session_factory() as db:
        agent = (
            await db.execute(select(Agent).where(Agent.key == ASSISTANT_AGENT_KEY))
        ).scalar_one_or_none()

        if not agent:
            return  # agent not seeded yet – skip silently

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
