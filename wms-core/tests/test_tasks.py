"""Tests for the tasks API (/api/tasks)."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, register_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TASK_PAYLOAD = {
    "title": "Test task",
    "description": "A test description",
    "status": "todo",
    "priority": "medium",
}


async def create_task(client: AsyncClient, **overrides) -> dict:
    payload = {**TASK_PAYLOAD, **overrides}
    resp = await client.post("/api/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def get_agent_id(client: AsyncClient, key: str = "task_automation") -> str:
    """Fetch agents list and return the id for the given key."""
    resp = await client.get("/api/agents")
    assert resp.status_code == 200
    agents = resp.json()
    agent = next((a for a in agents if a["key"] == key), None)
    assert agent is not None, f"No agent with key '{key}'"
    return agent["id"]


# ---------------------------------------------------------------------------
# POST /api/tasks  (create)
# ---------------------------------------------------------------------------


class TestCreateTask:
    async def test_create_task_success(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        assert task["title"] == "Test task"
        assert task["description"] == "A test description"
        assert task["status"] == "todo"
        assert task["priority"] == "medium"
        assert "id" in task
        assert "user_id" in task
        assert "created_at" in task
        assert "updated_at" in task

    async def test_create_task_with_agent_id(self, authed_client: AsyncClient):
        agent_id = await get_agent_id(authed_client)
        task = await create_task(authed_client, agent_id=agent_id)
        assert task["agent_id"] == agent_id
        assert task["assigned_agent"] == "task_automation"

    async def test_create_task_with_assigned_agent_key(
        self, authed_client: AsyncClient
    ):
        task = await create_task(authed_client, assigned_agent="notification")
        assert task["assigned_agent"] == "notification"
        assert task["agent_id"] is not None

    async def test_create_task_invalid_agent_id(self, authed_client: AsyncClient):
        resp = await authed_client.post(
            "/api/tasks", json={**TASK_PAYLOAD, "agent_id": "nonexistent"}
        )
        assert resp.status_code == 400

    async def test_create_task_with_due_date(self, authed_client: AsyncClient):
        task = await create_task(authed_client, due_date="2026-12-31")
        assert task["due_date"] == "2026-12-31"

    async def test_create_task_all_priorities(self, authed_client: AsyncClient):
        for p in ("low", "medium", "high"):
            task = await create_task(authed_client, priority=p, title=f"p-{p}")
            assert task["priority"] == p

    async def test_create_task_all_statuses(self, authed_client: AsyncClient):
        for s in ("todo", "in_progress", "done"):
            task = await create_task(authed_client, status=s, title=f"s-{s}")
            assert task["status"] == s

    async def test_create_task_unauthenticated(self, client: AsyncClient):
        resp = await client.post("/api/tasks", json=TASK_PAYLOAD)
        assert resp.status_code == 401

    async def test_create_task_missing_title(self, authed_client: AsyncClient):
        resp = await authed_client.post(
            "/api/tasks", json={"description": "no title here", "status": "todo"}
        )
        assert resp.status_code == 422

    async def test_create_task_invalid_agent_key(self, authed_client: AsyncClient):
        """assigned_agent with a key that doesn't exist should 400."""
        resp = await authed_client.post(
            "/api/tasks",
            json={**TASK_PAYLOAD, "assigned_agent": "nonexistent_agent_key"},
        )
        assert resp.status_code == 400
        assert "invalid agent key" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/tasks  (list)
# ---------------------------------------------------------------------------


class TestListTasks:
    async def test_list_empty(self, authed_client: AsyncClient):
        resp = await authed_client.get("/api/tasks")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_returns_own_tasks(self, authed_client: AsyncClient):
        await create_task(authed_client, title="T1")
        await create_task(authed_client, title="T2")
        resp = await authed_client.get("/api/tasks")
        assert resp.status_code == 200
        titles = {t["title"] for t in resp.json()}
        assert titles == {"T1", "T2"}

    async def test_isolation_between_users(self, client: AsyncClient):
        # User A
        a = await register_user(client, email="a@x.com", username="a")
        resp = await client.post(
            "/api/tasks",
            json=TASK_PAYLOAD,
            headers=auth_headers(a["access_token"]),
        )
        assert resp.status_code == 201

        # User B
        b = await register_user(client, email="b@x.com", username="b")
        resp = await client.get("/api/tasks", headers=auth_headers(b["access_token"]))
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/tasks/:id  (detail)
# ---------------------------------------------------------------------------


class TestGetTask:
    async def test_get_task_success(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.get(f"/api/tasks/{task['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task["id"]

    async def test_get_task_not_found(self, authed_client: AsyncClient):
        resp = await authed_client.get("/api/tasks/nonexistent-id")
        assert resp.status_code == 404

    async def test_get_task_other_user(self, client: AsyncClient):
        a = await register_user(client, email="owner@x.com", username="owner")
        resp = await client.post(
            "/api/tasks",
            json=TASK_PAYLOAD,
            headers=auth_headers(a["access_token"]),
        )
        task_id = resp.json()["id"]

        b = await register_user(client, email="other@x.com", username="other")
        resp = await client.get(
            f"/api/tasks/{task_id}", headers=auth_headers(b["access_token"])
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/tasks/:id  (update)
# ---------------------------------------------------------------------------


class TestUpdateTask:
    async def test_update_title(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}", json={"title": "Updated"}
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    async def test_update_description(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}", json={"description": "New desc"}
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "New desc"

    async def test_update_priority(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}", json={"priority": "high"}
        )
        assert resp.status_code == 200
        assert resp.json()["priority"] == "high"

    async def test_update_agent_by_id(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        agent_id = await get_agent_id(authed_client, "analytics")
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}", json={"agent_id": agent_id}
        )
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == agent_id
        assert resp.json()["assigned_agent"] == "analytics"

    async def test_update_agent_by_key(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}", json={"assigned_agent": "assistant"}
        )
        assert resp.status_code == 200
        assert resp.json()["assigned_agent"] == "assistant"

    async def test_unassign_agent(self, authed_client: AsyncClient):
        agent_id = await get_agent_id(authed_client)
        task = await create_task(authed_client, agent_id=agent_id)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}", json={"agent_id": None}
        )
        assert resp.status_code == 200
        assert resp.json()["agent_id"] is None
        assert resp.json()["assigned_agent"] is None

    async def test_update_due_date(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}", json={"due_date": "2026-06-15"}
        )
        assert resp.status_code == 200
        assert resp.json()["due_date"] == "2026-06-15"

    async def test_update_multiple_fields(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}",
            json={"title": "Multi", "priority": "high", "status": "in_progress"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Multi"
        assert body["priority"] == "high"
        assert body["status"] == "in_progress"

    async def test_update_not_found(self, authed_client: AsyncClient):
        resp = await authed_client.put("/api/tasks/nonexistent", json={"title": "x"})
        assert resp.status_code == 404

    async def test_update_other_user_task(self, client: AsyncClient):
        a = await register_user(client, email="orig@x.com", username="orig")
        resp = await client.post(
            "/api/tasks",
            json=TASK_PAYLOAD,
            headers=auth_headers(a["access_token"]),
        )
        task_id = resp.json()["id"]

        b = await register_user(client, email="intruder@x.com", username="intruder")
        resp = await client.put(
            f"/api/tasks/{task_id}",
            json={"title": "hacked"},
            headers=auth_headers(b["access_token"]),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/tasks/:id
# ---------------------------------------------------------------------------


class TestDeleteTask:
    async def test_delete_success(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.delete(f"/api/tasks/{task['id']}")
        assert resp.status_code == 204

        # Verify gone
        resp = await authed_client.get(f"/api/tasks/{task['id']}")
        assert resp.status_code == 404

    async def test_delete_not_found(self, authed_client: AsyncClient):
        resp = await authed_client.delete("/api/tasks/nonexistent")
        assert resp.status_code == 404

    async def test_delete_other_user(self, client: AsyncClient):
        a = await register_user(client, email="del_own@x.com", username="own")
        resp = await client.post(
            "/api/tasks",
            json=TASK_PAYLOAD,
            headers=auth_headers(a["access_token"]),
        )
        task_id = resp.json()["id"]

        b = await register_user(client, email="del_other@x.com", username="other")
        resp = await client.delete(
            f"/api/tasks/{task_id}",
            headers=auth_headers(b["access_token"]),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/tasks/:id/status
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    async def test_update_status_success(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}/status", json={"status": "in_progress"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    async def test_update_status_to_done(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}/status", json={"status": "done"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"

    async def test_update_status_invalid(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}/status", json={"status": "invalid_status"}
        )
        assert resp.status_code == 422

    async def test_update_status_not_found(self, authed_client: AsyncClient):
        resp = await authed_client.put(
            "/api/tasks/nonexistent/status", json={"status": "done"}
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/tasks/:id/assign
# ---------------------------------------------------------------------------


class TestAssignAgent:
    async def test_assign_by_agent_id(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        agent_id = await get_agent_id(authed_client, "notification")
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}/assign", json={"agent_id": agent_id}
        )
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == agent_id
        assert resp.json()["assigned_agent"] == "notification"

    async def test_assign_by_key(self, authed_client: AsyncClient):
        task = await create_task(authed_client)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}/assign",
            json={"assigned_agent": "analytics"},
        )
        assert resp.status_code == 200
        assert resp.json()["assigned_agent"] == "analytics"

    async def test_unassign(self, authed_client: AsyncClient):
        agent_id = await get_agent_id(authed_client)
        task = await create_task(authed_client, agent_id=agent_id)
        resp = await authed_client.put(
            f"/api/tasks/{task['id']}/assign",
            json={"agent_id": None, "assigned_agent": None},
        )
        assert resp.status_code == 200
        assert resp.json()["agent_id"] is None

    async def test_assign_not_found(self, authed_client: AsyncClient):
        resp = await authed_client.put(
            "/api/tasks/nonexistent/assign", json={"agent_id": None}
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# User assignment tests
# ---------------------------------------------------------------------------


class TestUserAssignment:
    """Tests for assigning tasks to users (assigned_user_id)."""

    async def test_create_task_with_assigned_user(self, client: AsyncClient):
        data = await register_user(client, email="creator@x.com", username="creator")
        headers = auth_headers(data["access_token"])
        user_id = data["user"]["id"]

        resp = await client.post(
            "/api/tasks",
            json={**TASK_PAYLOAD, "assigned_user_id": user_id},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["assigned_user_id"] == user_id
        assert body["assigned_username"] == "creator"
        assert body["agent_id"] is None

    async def test_create_task_user_overrides_agent(self, client: AsyncClient):
        """When both assigned_user_id and agent_id are set, user wins."""
        data = await register_user(client, email="both@x.com", username="both")
        headers = auth_headers(data["access_token"])
        user_id = data["user"]["id"]

        # Get an agent id
        resp = await client.get("/api/agents", headers=headers)
        agent_id = resp.json()[0]["id"]

        resp = await client.post(
            "/api/tasks",
            json={
                **TASK_PAYLOAD,
                "assigned_user_id": user_id,
                "agent_id": agent_id,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["assigned_user_id"] == user_id
        assert body["agent_id"] is None

    async def test_create_task_invalid_user_id(self, authed_client: AsyncClient):
        resp = await authed_client.post(
            "/api/tasks",
            json={**TASK_PAYLOAD, "assigned_user_id": "nonexistent-user"},
        )
        assert resp.status_code == 400
        assert "invalid user id" in resp.json()["detail"].lower()

    async def test_update_assign_user(self, client: AsyncClient):
        data = await register_user(client, email="upd@x.com", username="updater")
        headers = auth_headers(data["access_token"])
        user_id = data["user"]["id"]

        resp = await client.post("/api/tasks", json=TASK_PAYLOAD, headers=headers)
        task_id = resp.json()["id"]

        resp = await client.put(
            f"/api/tasks/{task_id}",
            json={"assigned_user_id": user_id},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["assigned_user_id"] == user_id
        assert body["assigned_username"] == "updater"

    async def test_update_user_clears_agent(self, client: AsyncClient):
        """Assigning a user via update should clear agent."""
        data = await register_user(client, email="clr@x.com", username="clearer")
        headers = auth_headers(data["access_token"])
        user_id = data["user"]["id"]

        # Create task with agent
        resp = await client.get("/api/agents", headers=headers)
        agent_id = resp.json()[0]["id"]
        resp = await client.post(
            "/api/tasks",
            json={**TASK_PAYLOAD, "agent_id": agent_id},
            headers=headers,
        )
        task_id = resp.json()["id"]

        # Update to assign user
        resp = await client.put(
            f"/api/tasks/{task_id}",
            json={"assigned_user_id": user_id},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["assigned_user_id"] == user_id
        assert body["agent_id"] is None

    async def test_update_agent_clears_user(self, client: AsyncClient):
        """Assigning an agent via update should clear assigned user."""
        data = await register_user(client, email="acl@x.com", username="aclearer")
        headers = auth_headers(data["access_token"])
        user_id = data["user"]["id"]

        # Create task with user
        resp = await client.post(
            "/api/tasks",
            json={**TASK_PAYLOAD, "assigned_user_id": user_id},
            headers=headers,
        )
        task_id = resp.json()["id"]

        # Update to assign agent
        resp = await client.get("/api/agents", headers=headers)
        agent_id = resp.json()[0]["id"]
        resp = await client.put(
            f"/api/tasks/{task_id}",
            json={"agent_id": agent_id},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_id"] == agent_id
        assert body["assigned_user_id"] is None

    async def test_assign_endpoint_user(self, client: AsyncClient):
        """PUT /assign with assigned_user_id."""
        data = await register_user(client, email="asg@x.com", username="assigner")
        headers = auth_headers(data["access_token"])
        user_id = data["user"]["id"]

        resp = await client.post("/api/tasks", json=TASK_PAYLOAD, headers=headers)
        task_id = resp.json()["id"]

        resp = await client.put(
            f"/api/tasks/{task_id}/assign",
            json={"assigned_user_id": user_id},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["assigned_user_id"] == user_id
        assert body["agent_id"] is None

    async def test_assign_endpoint_user_clears_agent(self, client: AsyncClient):
        """Assigning user via /assign endpoint should clear agent."""
        data = await register_user(client, email="auclr@x.com", username="auclr")
        headers = auth_headers(data["access_token"])
        user_id = data["user"]["id"]

        resp = await client.get("/api/agents", headers=headers)
        agent_id = resp.json()[0]["id"]

        resp = await client.post(
            "/api/tasks",
            json={**TASK_PAYLOAD, "agent_id": agent_id},
            headers=headers,
        )
        task_id = resp.json()["id"]

        resp = await client.put(
            f"/api/tasks/{task_id}/assign",
            json={"assigned_user_id": user_id},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["assigned_user_id"] == user_id
        assert body["agent_id"] is None

    async def test_unassign_user(self, client: AsyncClient):
        data = await register_user(client, email="unx@x.com", username="unassigner")
        headers = auth_headers(data["access_token"])
        user_id = data["user"]["id"]

        resp = await client.post(
            "/api/tasks",
            json={**TASK_PAYLOAD, "assigned_user_id": user_id},
            headers=headers,
        )
        task_id = resp.json()["id"]

        resp = await client.put(
            f"/api/tasks/{task_id}",
            json={"assigned_user_id": None},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["assigned_user_id"] is None
        assert resp.json()["assigned_username"] is None
