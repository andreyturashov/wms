from datetime import datetime

from pydantic import BaseModel


class AgentBase(BaseModel):
    key: str
    name: str
    description: str = ""
    is_active: bool = True


class AgentCreate(AgentBase):
    pass


class AgentResponse(AgentBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
