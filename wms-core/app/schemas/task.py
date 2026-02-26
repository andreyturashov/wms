from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TaskStatus = Literal["todo", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]


class TaskBase(BaseModel):
    title: str
    description: str = ""
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    agent_id: str | None = None
    assigned_agent: str | None = None
    assigned_user_id: str | None = None
    due_date: str | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    agent_id: str | None = None
    assigned_agent: str | None = None
    assigned_user_id: str | None = None
    due_date: str | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskAssignmentUpdate(BaseModel):
    agent_id: str | None = None
    assigned_agent: str | None = None
    assigned_user_id: str | None = None


class TaskResponse(TaskBase):
    id: str
    user_id: str
    assigned_username: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
