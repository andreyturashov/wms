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
        # Task creation auto-generates an AI analysis comment
        comments = resp.json()
        assert len(comments) == 1
        assert comments[0]["author_type"] == "agent"

    async def test_returns_comments(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        await create_comment(authed_client, task["id"], content="First")
        await create_comment(authed_client, task["id"], content="Second")

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        assert resp.status_code == 200
        comments = resp.json()
        # 1 AI auto-comment + 2 manual
        assert len(comments) == 3
        assert comments[1]["content"] == "First"
        assert comments[2]["content"] == "Second"

    async def test_comments_ordered_by_created_at(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        await create_comment(authed_client, task["id"], content="A")
        await create_comment(authed_client, task["id"], content="B")
        await create_comment(authed_client, task["id"], content="C")

        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()
        # First is the AI auto-comment, then A, B, C
        contents = [c["content"] for c in comments[1:]]
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
        comment = await create_comment(authed_client, task["id"], content="Agent says hi", agent_id=agent_id)

        assert comment["content"] == "Agent says hi"
        assert comment["user_id"] is None
        assert comment["agent_id"] == agent_id
        assert comment["author_type"] == "agent"
        assert comment["author_name"] != ""

    async def test_empty_content(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.post(f"/api/tasks/{task['id']}/comments", json={"content": "   "})
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
        resp = await authed_client.post("/api/tasks/nonexistent/comments", json={"content": "test"})
        assert resp.status_code == 404

    async def test_other_users_task(self, client: AsyncClient):
        user_a = await register_user(client, email="a@test.com", username="userA")
        client.headers.update(auth_headers(user_a["access_token"]))
        task = await create_task(client)

        user_b = await register_user(client, email="b@test.com", username="userB")
        client.headers.update(auth_headers(user_b["access_token"]))

        resp = await client.post(f"/api/tasks/{task['id']}/comments", json={"content": "sneaky"})
        assert resp.status_code == 404

    async def test_content_is_trimmed(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        comment = await create_comment(authed_client, task["id"], content="  padded  ")
        assert comment["content"] == "padded"

    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.post("/api/tasks/some-id/comments", json={"content": "test"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/tasks/{task_id}/comments/{comment_id}
# ---------------------------------------------------------------------------


class TestDeleteComment:
    async def test_delete_comment(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        comment = await create_comment(authed_client, task["id"])

        resp = await authed_client.delete(f"/api/tasks/{task['id']}/comments/{comment['id']}")
        assert resp.status_code == 204

        # Verify it's gone – only the AI auto-comment remains
        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        remaining = resp.json()
        assert len(remaining) == 1
        assert remaining[0]["author_type"] == "agent"

    async def test_delete_nonexistent_comment(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.delete(f"/api/tasks/{task['id']}/comments/nonexistent")
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
        comment = await create_comment(authed_client, task["id"], content="agent note", agent_id=agent_id)

        resp = await authed_client.delete(f"/api/tasks/{task['id']}/comments/{comment['id']}")
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
            "task_title",
            "content",
            "user_id",
            "agent_id",
            "author_name",
            "author_type",
            "parent_id",
            "replies",
            "created_at",
        }
        assert expected_keys == set(comment.keys())

    async def test_task_title_populated(self, authed_client: AsyncClient):
        task = await create_task(authed_client, title="My Special Task")
        comment = await create_comment(authed_client, task["id"], content="hello")
        assert comment["task_title"] == "My Special Task"


# ---------------------------------------------------------------------------
# GET /api/comments?user_id=...&agent_id=...
# ---------------------------------------------------------------------------


class TestGetCommentsByAuthor:
    async def test_get_by_user_id(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        c = await create_comment(authed_client, task["id"], content="user comment")
        user_id = c["user_id"]

        resp = await authed_client.get(f"/api/comments?user_id={user_id}")
        assert resp.status_code == 200
        comments = resp.json()
        assert len(comments) >= 1
        assert all(c["user_id"] == user_id for c in comments)

    async def test_get_by_agent_id(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        agent_id = await get_agent_id(authed_client)
        await create_comment(authed_client, task["id"], content="agent comment", agent_id=agent_id)

        resp = await authed_client.get(f"/api/comments?agent_id={agent_id}")
        assert resp.status_code == 200
        comments = resp.json()
        assert len(comments) == 1
        assert comments[0]["agent_id"] == agent_id
        assert comments[0]["content"] == "agent comment"

    async def test_includes_task_title(self, authed_client: AsyncClient):
        task = await create_task(authed_client, title="Special Task")
        await create_comment(authed_client, task["id"], content="with title")

        resp = await authed_client.get(f"/api/comments?user_id={task['user_id']}")
        comments = resp.json()
        assert any(c["task_title"] == "Special Task" for c in comments)

    async def test_no_params_returns_400(self, authed_client: AsyncClient):
        resp = await authed_client.get("/api/comments")
        assert resp.status_code == 400

    async def test_empty_when_no_comments(self, authed_client: AsyncClient):
        resp = await authed_client.get("/api/comments?user_id=nonexistent")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_only_own_task_comments(self, client: AsyncClient):
        """User B should not see comments on User A's tasks."""
        user_a = await register_user(client, email="a@author.com", username="userA")
        client.headers.update(auth_headers(user_a["access_token"]))
        task = await create_task(client)
        c = await create_comment(client, task["id"], content="private")
        user_a_id = c["user_id"]

        # User B queries for user A's comments — should see nothing
        user_b = await register_user(client, email="b@author.com", username="userB")
        client.headers.update(auth_headers(user_b["access_token"]))
        resp = await client.get(f"/api/comments?user_id={user_a_id}")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_comments_across_multiple_tasks(self, authed_client: AsyncClient):
        task1 = await create_task(authed_client, title="Task One")
        task2 = await create_task(authed_client, title="Task Two")
        await create_comment(authed_client, task1["id"], content="c1")
        await create_comment(authed_client, task2["id"], content="c2")
        c = await create_comment(authed_client, task1["id"], content="c3")
        user_id = c["user_id"]

        resp = await authed_client.get(f"/api/comments?user_id={user_id}")
        comments = resp.json()
        assert len(comments) == 3
        titles = {c["task_title"] for c in comments}
        assert titles == {"Task One", "Task Two"}

    async def test_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/comments?user_id=some-id")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Threaded / nested comments
# ---------------------------------------------------------------------------


@pytest.mark.anyio
class TestThreadedComments:
    async def test_reply_to_comment(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        parent = await create_comment(authed_client, task["id"], content="parent")
        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "reply", "parent_id": parent["id"]},
        )
        assert resp.status_code == 201
        reply = resp.json()
        assert reply["parent_id"] == parent["id"]
        assert reply["content"] == "reply"

    async def test_reply_appears_nested_in_get(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        parent = await create_comment(authed_client, task["id"], content="top")
        await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "nested", "parent_id": parent["id"]},
        )
        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        comments = resp.json()
        # AI auto-comment + the parent (top-level only)
        assert len(comments) == 2
        user_comment = next(c for c in comments if c["id"] == parent["id"])
        assert len(user_comment["replies"]) == 1
        assert user_comment["replies"][0]["content"] == "nested"

    async def test_top_level_has_null_parent_id(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        comment = await create_comment(authed_client, task["id"], content="top")
        assert comment["parent_id"] is None

    async def test_reply_to_nonexistent_parent(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "orphan", "parent_id": "no-such-id"},
        )
        assert resp.status_code == 400
        assert "Parent comment not found" in resp.json()["detail"]

    async def test_reply_to_comment_on_different_task(self, authed_client: AsyncClient):
        task1 = await create_task(authed_client, title="Task 1")
        task2 = await create_task(authed_client, title="Task 2")
        parent = await create_comment(authed_client, task1["id"], content="t1 comment")
        # Try to reply under task2 using parent from task1
        resp = await authed_client.post(
            f"/api/tasks/{task2['id']}/comments",
            json={"content": "cross-task", "parent_id": parent["id"]},
        )
        assert resp.status_code == 400

    async def test_delete_parent_cascades_replies(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        parent = await create_comment(authed_client, task["id"], content="parent")
        await authed_client.post(
            f"/api/tasks/{task['id']}/comments",
            json={"content": "child", "parent_id": parent["id"]},
        )
        # Delete parent
        resp = await authed_client.delete(f"/api/tasks/{task['id']}/comments/{parent['id']}")
        assert resp.status_code == 204
        # Only the AI auto-comment remains
        resp = await authed_client.get(f"/api/tasks/{task['id']}/comments")
        remaining = resp.json()
        assert len(remaining) == 1
        assert remaining[0]["author_type"] == "agent"
