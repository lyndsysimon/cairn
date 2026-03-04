"""Tests for the webhook trigger route."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from cairn.models.agent import AgentDefinition, AgentStatus
from cairn.models.run import AgentRun, RunStatus
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.trigger import WebhookTrigger


def _make_webhook_agent(
    path: str = "/hooks/my-agent",
    status: AgentStatus = AgentStatus.ACTIVE,
) -> AgentDefinition:
    return AgentDefinition(
        name="webhook-agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        output_schema={"type": "object"},
        trigger=WebhookTrigger(path=path),
        runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
        status=status,
    )


@pytest.fixture
async def webhook_client():
    """AsyncClient with DB and execution service dependencies overridden."""
    from cairn.api.dependencies import get_db_connection, get_execution_service
    from cairn.main import app

    mock_conn = AsyncMock()
    mock_conn.commit = AsyncMock()

    async def override_db():
        return mock_conn

    def override_execution():
        return AsyncMock()

    app.dependency_overrides[get_db_connection] = override_db
    app.dependency_overrides[get_execution_service] = override_execution

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c, mock_conn

    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestReceiveWebhook:
    """Tests for POST /api/webhooks/{path}."""

    async def test_triggers_matching_agent(self, webhook_client):
        """A webhook POST to a registered path creates and executes a run."""
        client, mock_conn = webhook_client
        agent = _make_webhook_agent("/hooks/my-agent")
        run = AgentRun(agent_id=agent.id, input_data={"message": "hello"})

        with (
            patch("cairn.api.routes.webhooks.agent_repo") as mock_agent_repo,
            patch("cairn.api.routes.webhooks.run_repo") as mock_run_repo,
            patch("cairn.api.routes.webhooks._run_agent", new_callable=AsyncMock),
        ):
            mock_agent_repo.get_by_webhook_path = AsyncMock(return_value=agent)
            mock_run_repo.create = AsyncMock(return_value=run)

            resp = await client.post(
                "/api/webhooks/hooks/my-agent",
                json={"message": "hello"},
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data["agent_id"] == str(agent.id)
        assert data["status"] == RunStatus.PENDING
        assert data["input_data"] == {"message": "hello"}

        mock_agent_repo.get_by_webhook_path.assert_called_once()
        call_args = mock_agent_repo.get_by_webhook_path.call_args
        assert call_args[0][1] == "/hooks/my-agent"

        mock_run_repo.create.assert_called_once()

    async def test_returns_404_for_unknown_path(self, webhook_client):
        """A webhook POST to an unregistered path returns 404."""
        client, _ = webhook_client

        with patch("cairn.api.routes.webhooks.agent_repo") as mock_agent_repo:
            mock_agent_repo.get_by_webhook_path = AsyncMock(return_value=None)

            resp = await client.post(
                "/api/webhooks/hooks/nonexistent",
                json={"data": "test"},
            )

        assert resp.status_code == 404
        assert "No agent registered" in resp.json()["detail"]

    async def test_empty_body_sends_null_input(self, webhook_client):
        """A webhook POST with no body passes None as input_data."""
        client, _ = webhook_client
        agent = _make_webhook_agent("/hooks/no-body")
        run = AgentRun(agent_id=agent.id, input_data=None)

        with (
            patch("cairn.api.routes.webhooks.agent_repo") as mock_agent_repo,
            patch("cairn.api.routes.webhooks.run_repo") as mock_run_repo,
            patch("cairn.api.routes.webhooks._run_agent", new_callable=AsyncMock),
        ):
            mock_agent_repo.get_by_webhook_path = AsyncMock(return_value=agent)
            mock_run_repo.create = AsyncMock(return_value=run)

            resp = await client.post("/api/webhooks/hooks/no-body")

        assert resp.status_code == 202
        data = resp.json()
        assert data["input_data"] is None

        created_run = mock_run_repo.create.call_args[0][1]
        assert created_run.input_data is None

    async def test_invalid_json_returns_400(self, webhook_client):
        """A webhook POST with non-JSON body returns 400."""
        client, _ = webhook_client
        agent = _make_webhook_agent("/hooks/bad-json")

        with patch("cairn.api.routes.webhooks.agent_repo") as mock_agent_repo:
            mock_agent_repo.get_by_webhook_path = AsyncMock(return_value=agent)

            resp = await client.post(
                "/api/webhooks/hooks/bad-json",
                content=b"this is not json",
                headers={"content-type": "application/json"},
            )

        assert resp.status_code == 400
        assert "not valid JSON" in resp.json()["detail"]

    async def test_nested_webhook_path(self, webhook_client):
        """Webhook paths with multiple segments work correctly."""
        client, _ = webhook_client
        agent = _make_webhook_agent("/org/team/deploy")
        run = AgentRun(agent_id=agent.id, input_data={"ref": "main"})

        with (
            patch("cairn.api.routes.webhooks.agent_repo") as mock_agent_repo,
            patch("cairn.api.routes.webhooks.run_repo") as mock_run_repo,
            patch("cairn.api.routes.webhooks._run_agent", new_callable=AsyncMock),
        ):
            mock_agent_repo.get_by_webhook_path = AsyncMock(return_value=agent)
            mock_run_repo.create = AsyncMock(return_value=run)

            resp = await client.post(
                "/api/webhooks/org/team/deploy",
                json={"ref": "main"},
            )

        assert resp.status_code == 202
        call_args = mock_agent_repo.get_by_webhook_path.call_args
        assert call_args[0][1] == "/org/team/deploy"

    async def test_run_is_committed_to_db(self, webhook_client):
        """The run creation is committed before returning."""
        client, mock_conn = webhook_client
        agent = _make_webhook_agent("/hooks/commit-check")
        run = AgentRun(agent_id=agent.id, input_data=None)

        with (
            patch("cairn.api.routes.webhooks.agent_repo") as mock_agent_repo,
            patch("cairn.api.routes.webhooks.run_repo") as mock_run_repo,
            patch("cairn.api.routes.webhooks._run_agent", new_callable=AsyncMock),
        ):
            mock_agent_repo.get_by_webhook_path = AsyncMock(return_value=agent)
            mock_run_repo.create = AsyncMock(return_value=run)

            resp = await client.post("/api/webhooks/hooks/commit-check")

        assert resp.status_code == 202
        mock_conn.commit.assert_called_once()

    async def test_background_execution_is_scheduled(self, webhook_client):
        """The background task _run_agent is scheduled with the correct args."""
        client, _ = webhook_client
        agent = _make_webhook_agent("/hooks/bg-check")
        run = AgentRun(agent_id=agent.id, input_data={"x": 1})

        with (
            patch("cairn.api.routes.webhooks.agent_repo") as mock_agent_repo,
            patch("cairn.api.routes.webhooks.run_repo") as mock_run_repo,
            patch(
                "cairn.api.routes.webhooks._run_agent", new_callable=AsyncMock
            ) as mock_run_agent,
        ):
            mock_agent_repo.get_by_webhook_path = AsyncMock(return_value=agent)
            mock_run_repo.create = AsyncMock(return_value=run)

            resp = await client.post(
                "/api/webhooks/hooks/bg-check",
                json={"x": 1},
            )

        assert resp.status_code == 202
        mock_run_agent.assert_called_once()
        call_args = mock_run_agent.call_args[0]
        assert call_args[0].id == agent.id
        assert call_args[1].id == run.id
