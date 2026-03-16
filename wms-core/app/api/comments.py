import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.agent_mention import handle_agent_mentions, handle_agent_reply
from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.agent import Agent
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse

router = APIRouter()

# Separate router for /api/comments (not nested under a task)
comments_router = APIRouter()


@comments_router.get("", response_model=list[CommentResponse])
async def get_comments_by_author(
    user_id: str | None = Query(None),
    agent_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all comments authored by a given user or agent (across tasks owned by current user)."""
    if not user_id and not agent_id:
        raise HTTPException(status_code=400, detail="Provide user_id or agent_id query parameter")

    # Only return comments on tasks owned by the current user
    query = select(Comment).join(Task, Comment.task_id == Task.id).where(Task.user_id == current_user.id)

    if user_id:
        query = query.where(Comment.user_id == user_id)
    elif agent_id:
        query = query.where(Comment.agent_id == agent_id)

    query = query.order_by(Comment.created_at.desc())
    query = query.options(selectinload(Comment.replies))
    result = await db.execute(query)
    return result.scalars().all()


@comments_router.get("/mentions", response_model=list[CommentResponse])
async def get_comments_mentioning_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all comments that @mention the current user (across their tasks)."""
    pattern = f"%@{current_user.username}%"
    query = (
        select(Comment)
        .join(Task, Comment.task_id == Task.id)
        .where(Task.user_id == current_user.id, Comment.content.like(pattern))
        .order_by(Comment.created_at.desc())
        .options(selectinload(Comment.replies))
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{task_id}/comments", response_model=list[CommentResponse])
async def get_task_comments(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify task belongs to the user
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")

    # Load ALL comments for this task (flat) and build the nested tree in code
    # so there is no hard limit on nesting depth.
    result = await db.execute(select(Comment).where(Comment.task_id == task_id).order_by(Comment.created_at.asc()))
    all_comments = result.scalars().all()

    # Build tree: assign children into parent.replies
    by_id: dict[str, Comment] = {}
    roots: list[Comment] = []
    for c in all_comments:
        c.replies = []  # type: ignore[assignment]
        by_id[c.id] = c
    for c in all_comments:
        if c.parent_id:
            parent = by_id.get(c.parent_id)
            if parent:
                parent.replies.append(c)  # type: ignore[arg-type]
            # Orphaned reply (parent was deleted) — skip it entirely
        else:
            roots.append(c)

    return roots


@router.post(
    "/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_comment(
    task_id: str,
    payload: CommentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify task belongs to the user
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")

    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Comment content cannot be empty")

    # Determine author: agent_id takes priority if provided
    user_id = None
    agent_id = None

    if payload.agent_id:
        result = await db.execute(select(Agent).where(Agent.id == payload.agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=400, detail="Invalid agent id")
        agent_id = agent.id
    else:
        user_id = current_user.id

    comment = Comment(
        id=str(uuid.uuid4()),
        task_id=task_id,
        content=payload.content.strip(),
        user_id=user_id,
        agent_id=agent_id,
        parent_id=None,
    )

    # Validate parent_id if provided
    parent_comment = None
    if payload.parent_id:
        parent_result = await db.execute(
            select(Comment).where(Comment.id == payload.parent_id, Comment.task_id == task_id)
        )
        parent_comment = parent_result.scalar_one_or_none()
        if not parent_comment:
            raise HTTPException(status_code=400, detail="Parent comment not found in this task")
        comment.parent_id = payload.parent_id

    db.add(comment)
    await db.commit()

    # Schedule agent mention reactions in the background so the HTTP
    # response returns immediately (LLM inference can take many seconds).
    background_tasks.add_task(
        handle_agent_mentions,
        task_id=task_id,
        comment_id=comment.id,
        comment_content=comment.content,
    )

    # If user is replying to an agent comment (and didn't already @mention
    # that agent), auto-trigger the agent to continue the conversation.
    if (
        parent_comment and parent_comment.agent_id and not payload.agent_id  # user comment, not agent posting
    ):
        background_tasks.add_task(
            handle_agent_reply,
            task_id=task_id,
            comment_id=comment.id,
            comment_content=comment.content,
            parent_agent_id=parent_comment.agent_id,
        )

    # Re-fetch with relationships loaded
    result = await db.execute(
        select(Comment)
        .where(Comment.id == comment.id)
        .options(selectinload(Comment.replies))
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


@router.delete(
    "/{task_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task_comment(
    task_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify task belongs to the user
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")

    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.task_id == task_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    await db.delete(comment)
    await db.commit()
