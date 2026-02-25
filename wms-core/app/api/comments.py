import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
    user_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all comments authored by a given user or agent (across tasks owned by current user)."""
    if not user_id and not agent_id:
        raise HTTPException(
            status_code=400, detail="Provide user_id or agent_id query parameter"
        )

    # Only return comments on tasks owned by the current user
    query = (
        select(Comment)
        .join(Task, Comment.task_id == Task.id)
        .where(Task.user_id == current_user.id)
    )

    if user_id:
        query = query.where(Comment.user_id == user_id)
    elif agent_id:
        query = query.where(Comment.agent_id == agent_id)

    query = query.order_by(Comment.created_at.desc())
    query = query.options(selectinload(Comment.replies))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{task_id}/comments", response_model=list[CommentResponse])
async def get_task_comments(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify task belongs to the user
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")

    # Return only top-level comments; replies are nested via the relationship
    result = await db.execute(
        select(Comment)
        .where(Comment.task_id == task_id, Comment.parent_id.is_(None))
        .options(selectinload(Comment.replies).selectinload(Comment.replies))
        .order_by(Comment.created_at.asc())
    )
    return result.scalars().all()


@router.post(
    "/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_comment(
    task_id: str,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify task belongs to the user
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
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
    if payload.parent_id:
        parent_result = await db.execute(
            select(Comment).where(
                Comment.id == payload.parent_id, Comment.task_id == task_id
            )
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="Parent comment not found in this task"
            )
        comment.parent_id = payload.parent_id

    db.add(comment)
    await db.commit()
    # Re-fetch with relationships loaded
    result = await db.execute(
        select(Comment)
        .where(Comment.id == comment.id)
        .options(selectinload(Comment.replies))
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
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")

    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.task_id == task_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    await db.delete(comment)
    await db.commit()
