"""Tests for the agents API (/api/agents)."""

from httpx import AsyncClient

# ---------------------------------------------------------------------------
# GET /api/agents
# ---------------------------------------------------------------------------


class TestListAgents:
    async def test_list_agents_success(self, authed_client: AsyncClient):
        resp = await authed_client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        # Default seed includes 2 agents
        assert len(agents) >= 2
        keys = {a["key"] for a in agents}
        assert keys >= {"executor", "thinker"}

    async def test_list_agents_active_only(self, authed_client: AsyncClient):
        resp = await authed_client.get("/api/agents?active_only=true")
        assert resp.status_code == 200
        agents = resp.json()
        assert all(a["is_active"] for a in agents)

    async def test_list_agents_includes_inactive(self, authed_client: AsyncClient):
        # Create an inactive agent, then fetch with active_only=false
        await authed_client.post(
            "/api/agents",
            json={
                "key": "inactive_bot",
                "name": "Inactive Bot",
                "description": "desc",
                "is_active": False,
            },
        )
        resp = await authed_client.get("/api/agents?active_only=false")
        assert resp.status_code == 200
        keys = {a["key"] for a in resp.json()}
        assert "inactive_bot" in keys

        # active_only should exclude it
        resp = await authed_client.get("/api/agents?active_only=true")
        keys_active = {a["key"] for a in resp.json()}
        assert "inactive_bot" not in keys_active

    async def test_list_agents_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/agents")
        assert resp.status_code == 401

    async def test_agents_ordered_by_name(self, authed_client: AsyncClient):
        resp = await authed_client.get("/api/agents")
        names = [a["name"] for a in resp.json()]
        assert names == sorted(names)

    async def test_agent_response_shape(self, authed_client: AsyncClient):
        resp = await authed_client.get("/api/agents")
        agent = resp.json()[0]
        assert "id" in agent
        assert "key" in agent
        assert "name" in agent
        assert "description" in agent
        assert "is_active" in agent
        assert "created_at" in agent
        assert "updated_at" in agent


# ---------------------------------------------------------------------------
# POST /api/agents
# ---------------------------------------------------------------------------


class TestCreateAgent:
    async def test_create_agent_success(self, authed_client: AsyncClient):
        resp = await authed_client.post(
            "/api/agents",
            json={"key": "new_agent", "name": "New Agent", "description": "A new bot"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["key"] == "new_agent"
        assert body["name"] == "New Agent"
        assert body["description"] == "A new bot"
        assert body["is_active"] is True
        assert "id" in body

    async def test_create_agent_inactive(self, authed_client: AsyncClient):
        resp = await authed_client.post(
            "/api/agents",
            json={"key": "off_agent", "name": "Off", "is_active": False},
        )
        assert resp.status_code == 201
        assert resp.json()["is_active"] is False

    async def test_create_agent_duplicate_key(self, authed_client: AsyncClient):
        # 'executor' is seeded by default
        resp = await authed_client.post(
            "/api/agents",
            json={"key": "executor", "name": "Dup"},
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    async def test_create_agent_missing_name(self, authed_client: AsyncClient):
        resp = await authed_client.post("/api/agents", json={"key": "noname"})
        assert resp.status_code == 422

    async def test_create_agent_missing_key(self, authed_client: AsyncClient):
        resp = await authed_client.post("/api/agents", json={"name": "No Key"})
        assert resp.status_code == 422

    async def test_create_agent_unauthenticated(self, client: AsyncClient):
        resp = await client.post(
            "/api/agents",
            json={"key": "sneaky", "name": "Sneaky"},
        )
        assert resp.status_code == 401
