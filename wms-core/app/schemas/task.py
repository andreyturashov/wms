from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional


TaskStatus = Literal["todo", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]


class TaskBase(BaseModel):
    title: str
    description: str = ""
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    agent_id: Optional[str] = None
    assigned_agent: Optional[str] = None
    assigned_user_id: Optional[str] = None
    due_date: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    agent_id: Optional[str] = None
    assigned_agent: Optional[str] = None
    assigned_user_id: Optional[str] = None
    due_date: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskAssignmentUpdate(BaseModel):
    agent_id: Optional[str] = None
    assigned_agent: Optional[str] = None
    assigned_user_id: Optional[str] = None


class TaskResponse(TaskBase):
    id: str
    user_id: str
    assigned_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
