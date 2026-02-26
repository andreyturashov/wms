"""Tests for Pydantic schemas and SQLAlchemy models."""

from datetime import datetime

import pytest

from app.models.agent import Agent as AgentModel
from app.models.task import Task as TaskModel
from app.models.user import User as UserModel
from app.schemas.agent import AgentBase, AgentCreate, AgentResponse
from app.schemas.task import (
    TaskAssignmentUpdate,
    TaskBase,
    TaskCreate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.schemas.user import Token, UserCreate, UserResponse

# ---------------------------------------------------------------------------
# Task schemas
# ---------------------------------------------------------------------------


class TestTaskSchemas:
    def test_task_base_defaults(self):
        t = TaskBase(title="My task")
        assert t.title == "My task"
        assert t.description == ""
        assert t.status == "todo"
        assert t.priority == "medium"
        assert t.agent_id is None
        assert t.assigned_agent is None
        assert t.assigned_user_id is None
        assert t.due_date is None

    def test_task_create_inherits_base(self):
        t = TaskCreate(title="Create me", status="in_progress", priority="high")
        assert t.status == "in_progress"
        assert t.priority == "high"

    def test_task_update_partial(self):
        t = TaskUpdate(title="Only title")
        data = t.model_dump(exclude_unset=True)
        assert data == {"title": "Only title"}

    def test_task_update_empty(self):
        t = TaskUpdate()
        data = t.model_dump(exclude_unset=True)
        assert data == {}

    def test_task_status_update_valid(self):
        s = TaskStatusUpdate(status="done")
        assert s.status == "done"

    def test_task_status_update_invalid(self):
        with pytest.raises(Exception):
            TaskStatusUpdate(status="invalid")

    def test_task_assignment_update(self):
        a = TaskAssignmentUpdate(agent_id="abc123")
        assert a.agent_id == "abc123"
        assert a.assigned_agent is None
        assert a.assigned_user_id is None

    def test_task_assignment_update_with_user(self):
        a = TaskAssignmentUpdate(assigned_user_id="user123")
        assert a.assigned_user_id == "user123"
        assert a.agent_id is None

    def test_task_response_from_model(self):
        now = datetime.utcnow()
        # Simulate a flat dict as if from ORM
        data = {
            "id": "t1",
            "title": "T",
            "description": "D",
            "status": "todo",
            "priority": "low",
            "agent_id": None,
            "assigned_agent": None,
            "assigned_user_id": None,
            "assigned_username": None,
            "due_date": None,
            "user_id": "u1",
            "created_at": now,
            "updated_at": now,
        }
        resp = TaskResponse(**data)
        assert resp.id == "t1"
        assert resp.user_id == "u1"
        assert resp.assigned_user_id is None
        assert resp.assigned_username is None


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class TestUserSchemas:
    def test_user_create(self):
        u = UserCreate(email="a@b.com", username="ab", password="secret")
        assert u.email == "a@b.com"
        assert u.password == "secret"

    def test_user_create_invalid_email(self):
        with pytest.raises(Exception):
            UserCreate(email="not-email", username="x", password="y")

    def test_user_response(self):
        u = UserResponse(id="u1", email="a@b.com", username="ab")
        assert u.id == "u1"

    def test_token_schema(self):
        t = Token(
            access_token="tok",
            token_type="bearer",
            user=UserResponse(id="u1", email="a@b.com", username="ab"),
        )
        assert t.access_token == "tok"
        assert t.user.email == "a@b.com"


# ---------------------------------------------------------------------------
# Agent schemas
# ---------------------------------------------------------------------------


class TestAgentSchemas:
    def test_agent_base_defaults(self):
        a = AgentBase(key="k", name="N")
        assert a.description == ""
        assert a.is_active is True

    def test_agent_create(self):
        a = AgentCreate(key="k", name="N", description="D", is_active=False)
        assert a.is_active is False

    def test_agent_response(self):
        now = datetime.utcnow()
        a = AgentResponse(
            id="a1",
            key="k",
            name="N",
            description="D",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert a.id == "a1"


# ---------------------------------------------------------------------------
# SQLAlchemy models (unit-level attribute checks, no DB)
# ---------------------------------------------------------------------------


class TestModels:
    def test_user_model_fields(self):
        u = UserModel(id="u1", email="a@b.com", username="ab", password_hash="hash")
        assert u.__tablename__ == "users"
        assert u.email == "a@b.com"

    def test_task_model_fields(self):
        t = TaskModel(
            id="t1",
            title="T",
            description="D",
            status="todo",
            priority="medium",
            user_id="u1",
        )
        assert t.__tablename__ == "tasks"
        assert t.agent_id is None

    def test_task_assigned_agent_property_no_agent(self):
        t = TaskModel(id="t1", title="T", user_id="u1")
        assert t.assigned_agent is None

    def test_task_assigned_username_property_no_user(self):
        t = TaskModel(id="t1", title="T", user_id="u1")
        assert t.assigned_username is None

    def test_task_model_assigned_user_id_field(self):
        t = TaskModel(id="t1", title="T", user_id="u1", assigned_user_id="u2")
        assert t.assigned_user_id == "u2"

    def test_agent_model_fields(self):
        a = AgentModel(
            id="a1",
            key="k",
            name="N",
            description="D",
            is_active=True,
        )
        assert a.__tablename__ == "agents"
        assert a.key == "k"
