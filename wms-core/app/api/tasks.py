from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from app.db.session import get_db
from app.models.agent import Agent
from app.models.user import User
from app.models.task import Task
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskStatusUpdate,
    TaskAssignmentUpdate,
)
from app.api.auth import get_current_user

router = APIRouter()


async def resolve_agent_by_id(
    agent_id: str | None,
    db: AsyncSession,
) -> Agent | None:
    if agent_id is None:
        return None

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=400, detail="Invalid agent id")
    return agent


async def resolve_agent_by_key(
    assigned_agent: str | None,
    db: AsyncSession,
) -> Agent | None:
    if assigned_agent is None:
        return None

    result = await db.execute(select(Agent).where(Agent.key == assigned_agent))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=400, detail="Invalid agent key")
    return agent


@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.user_id == current_user.id))
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await resolve_agent_by_id(task.agent_id, db)
    if not agent:
        agent = await resolve_agent_by_key(task.assigned_agent, db)

    new_task = Task(
        id=str(uuid.uuid4()),
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        agent_id=agent.id if agent else None,
        due_date=task.due_date,
        user_id=current_user.id,
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_update.model_dump(exclude_unset=True)
    assigned_agent_in_payload = "assigned_agent" in update_data
    assigned_agent_value = update_data.pop("assigned_agent", None)

    if "agent_id" in update_data:
        agent = await resolve_agent_by_id(update_data["agent_id"], db)
        task.agent_id = agent.id if agent else None
    elif assigned_agent_in_payload:
        agent = await resolve_agent_by_key(assigned_agent_value, db)
        task.agent_id = agent.id if agent else None

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: str,
    status_update: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = status_update.status
    await db.commit()
    await db.refresh(task)
    return task


@router.put("/{task_id}/assign", response_model=TaskResponse)
async def assign_task_agent(
    task_id: str,
    assignment: TaskAssignmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    agent = await resolve_agent_by_id(assignment.agent_id, db)
    if not agent:
        agent = await resolve_agent_by_key(assignment.assigned_agent, db)
    task.agent_id = agent.id if agent else None
    await db.commit()
    await db.refresh(task)
    return task
