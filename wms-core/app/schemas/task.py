from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TaskBase(BaseModel):
    title: str
    description: str = ""
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None


class TaskResponse(TaskBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
