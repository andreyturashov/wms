from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CommentCreate(BaseModel):
    content: str
    agent_id: Optional[str] = None


class CommentResponse(BaseModel):
    id: str
    task_id: str
    content: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    author_name: str
    author_type: str
    created_at: datetime

    class Config:
        from_attributes = True
