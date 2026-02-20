from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="todo")  # todo, in_progress, done
    priority = Column(String, default="medium")  # low, medium, high
    due_date = Column(String, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
