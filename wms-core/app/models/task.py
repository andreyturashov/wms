from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="todo")  # todo, in_progress, done
    priority = Column(String, default="medium")  # low, medium, high
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    assigned_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    due_date = Column(String, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", lazy="joined")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id], lazy="joined")

    @property
    def assigned_agent(self) -> str | None:
        if not self.agent:
            return None
        return self.agent.key

    @property
    def assigned_username(self) -> str | None:
        if not self.assigned_user:
            return None
        return self.assigned_user.username
