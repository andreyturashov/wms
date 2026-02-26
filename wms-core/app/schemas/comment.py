from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CommentCreate(BaseModel):
    content: str
    agent_id: str | None = None
    parent_id: str | None = None


class CommentResponse(BaseModel):
    id: str
    task_id: str
    task_title: str = ""
    content: str
    user_id: str | None = None
    agent_id: str | None = None
    author_name: str
    author_type: str
    parent_id: str | None = None
    replies: list[CommentResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True
