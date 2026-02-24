"""Tests for the comments API (/api/tasks/{task_id}/comments)."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, register_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TASK_PAYLOAD = {
    "title": "Commented task",
    "description": "Task with comments",
    "status": "todo",
    "priority": "medium",
}


async def create_task(client: AsyncClient, **overrides) -> dict:
    payload = {**TASK_PAYLOAD, **overrides}
    resp = await client.post("/api/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def get_agent_id(client: AsyncClient, key: str = "task_automation") -> str:
    resp = await client.get("/api/agents")
    assert resp.status_code == 200
    agents = resp.json()
    agent = next((a for a in agents if a["key"] == key), None)
    assert agent is not None, f"No agent with key '{key}'"
    return agent["id"]


async def create_comment(client: AsyncClient, task_id: str, **overrides) -> dict:
    payload = {"content": "Test comment", **overrides}
    resp = await client.post(f"/api/tasks/{task_id}/comments", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# GET /api/tasks/{task_id}/comments
# ---------------------------------------------------------------------------


class TestGetComments:
    async def test_empty_comments(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_comments(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        await create_comment(authed_client, task["id"], content="First")
        await create_comment(authed_client, task["id"], content="Second")

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        assert resp.status_code == 200
        comments = resp.json()
        assert len(comments) == 2
        assert comments[0]["content"] == "First"
        assert comments[1]["content"] == "Second"

    async def test_comments_ordered_by_created_at(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        await create_comment(authed_client, task["id"], content="A")
        await create_comment(authed_client, task["id"], content="B")
        await create_comment(authed_client, task["id"], content="C")

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()
        contents = [c["content"] for c in comments]
        assert contents == ["A", "B", "C"]

    async def test_task_not_found(self, authed_client: AsyncClient):
        resp = await authed_client.get("/api/tasks/nonexistent/comments")
        assert resp.status_code == 404

    async def test_other_users_task(self, client: AsyncClient):
        # User A creates a task
        user_a = await register_user(client, email="a@example.com", username="userA")
        client.headers.update(auth_headers(user_a["access_token"]))
        task = await create_task(client)

        # User B tries to get comments
        user_b = await register_user(client, email="b@example.com", username="userB")
        client.headers.update(auth_headers(user_b["access_token"]))

        resp = await client.get(f"/api/tasks/{task['id']}/comments")
        assert resp.status_code == 404

    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/tasks/some-id/comments")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/tasks/{task_id}/comments
# ---------------------------------------------------------------------------


class TestCreateComment:
    async def test_create_as_user(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        comment = await create_comment(authed_client, task["id"], content="Hello!")

        assert comment["content"] == "Hello!"
        assert comment["task_id"] == task["id"]
        assert comment["user_id"] is not None
        assert comment["agent_id"] is None
        assert comment["author_type"] == "user"
        assert comment["author_name"] == "testuser"
        assert "id" in comment
        assert "created_at" in comment

    async def test_create_as_agent(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        agent_id = await get_agent_id(authed_client)
        comment = await create_comment(
            authed_client, task["id"], content="Agent says hi", agent_id=agent_id
        )

        assert comment["content"] == "Agent says hi"
        assert comment["user_id"] is None
        assert comment["agent_id"] == agent_id
        assert comment["author_type"] == "agent"
        assert comment["author_name"] != ""

    async def test_empty_content(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments", json={"content": "   "}
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    async def test_invalid_agent_id(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "test", "agent_id": "bad-id"},
        )
        assert resp.status_code == 400
        assert "agent" in resp.json()["detail"].lower()

    async def test_task_not_found(self, authed_client: AsyncClient):
        resp = await authed_client.post(
            "/api/tasks/nonexistent/comments", json={"content": "test"}
        )
        assert resp.status_code == 404

    async def test_other_users_task(self, client: AsyncClient):
        user_a = await register_user(client, email="a@test.com", username="userA")
        client.headers.update(auth_headers(user_a["access_token"]))
        task = await create_task(client)

        user_b = await register_user(client, email="b@test.com", username="userB")
        client.headers.update(auth_headers(user_b["access_token"]))

        resp = await client.post(
            f"/api/tasks/{task['id']}/comments", json={"content": "sneaky"}
        )
        assert resp.status_code == 404

    async def test_content_is_trimmed(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        comment = await create_comment(authed_client, task["id"], content="  padded  ")
        assert comment["content"] == "padded"

    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.post(
            "/api/tasks/some-id/comments", json={"content": "test"}
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/tasks/{task_id}/comments/{comment_id}
# ---------------------------------------------------------------------------


class TestDeleteComment:
    async def test_delete_comment(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        comment = await create_comment(authed_client, task["id"])

        resp = await authed_client.delete(
            f"/api/tasks/{task['id']}/comments/{comment['id']}"
        )
        assert resp.status_code == 204

        # Verify it's gone
        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        assert resp.json() == []

    async def test_delete_nonexistent_comment(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.delete(
            f"/api/tasks/{task['id']}/comments/nonexistent"
        )
        assert resp.status_code == 404

    async def test_delete_task_not_found(self, authed_client: AsyncClient):
        resp = await authed_client.delete("/api/tasks/nonexistent/comments/nonexistent")
        assert resp.status_code == 404

    async def test_delete_other_users_task(self, client: AsyncClient):
        user_a = await register_user(client, email="a@del.com", username="userA")
        client.headers.update(auth_headers(user_a["access_token"]))
        task = await create_task(client)
        comment = await create_comment(client, task["id"])

        user_b = await register_user(client, email="b@del.com", username="userB")
        client.headers.update(auth_headers(user_b["access_token"]))

        resp = await client.delete(f"/api/tasks/{task['id']}/comments/{comment['id']}")
        assert resp.status_code == 404

    async def test_delete_agent_comment(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        agent_id = await get_agent_id(authed_client)
        comment = await create_comment(
            authed_client, task["id"], content="agent note", agent_id=agent_id
        )

        resp = await authed_client.delete(
            f"/api/tasks/{task['id']}/comments/{comment['id']}"
        )
        assert resp.status_code == 204

    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.delete("/api/tasks/some-id/comments/some-id")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Comment response shape
# ---------------------------------------------------------------------------


class TestCommentResponseShape:
    async def test_response_fields(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        comment = await create_comment(authed_client, task["id"], content="check shape")

        expected_keys = {
            "id",
            "task_id",
            "content",
            "user_id",
            "agent_id",
            "author_name",
            "author_type",
            "created_at",
        }
        assert expected_keys == set(comment.keys())
