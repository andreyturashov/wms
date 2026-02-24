from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Exactly one of user_id / agent_id should be set
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", lazy="joined")
    user = relationship("User", lazy="joined")
    agent = relationship("Agent", lazy="joined")

    @property
    def author_name(self) -> str:
        if self.user:
            return self.user.username
        if self.agent:
            return self.agent.name
        return "Unknown"

    @property
    def author_type(self) -> str:
        if self.user_id:
            return "user"
        if self.agent_id:
            return "agent"
        return "unknown"
