from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text

from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    system_prompt = Column(Text, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
