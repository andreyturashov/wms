from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CommentCreate(BaseModel):
    content: str
    agent_id: Optional[str] = None
    parent_id: Optional[str] = None


class CommentResponse(BaseModel):
    id: str
    task_id: str
    task_title: str = ""
    content: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    author_name: str
    author_type: str
    parent_id: Optional[str] = None
    replies: list[CommentResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True
