"""Tests for the agent execution service.

Uses fully mocked runtime, security, and database layers.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from cairn.execution.service import ExecutionService
from cairn.models.agent import AgentDefinition
from cairn.models.credential import CredentialReference, CredentialValue
from cairn.models.run import AgentRun, RunStatus
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.trigger import ManualTrigger


@pytest.fixture
def agent() -> AgentDefinition:
    return AgentDefinition(
        name="exec-test-agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger=ManualTrigger(),
        runtime=RuntimeConfig(
            type=RuntimeType.DOCKER,
            image="python:3.13-slim",
            timeout_seconds=10,
        ),
        credentials=[
            CredentialReference(
                store_name="postgres",
                credential_id="test-key",
                env_var_name="TEST_KEY",
            )
        ],
    )


@pytest.fixture
def pending_run(agent) -> AgentRun:
    return AgentRun(agent_id=agent.id, input_data={"query": "hello"})


def _make_runtime(
    start_status: RunStatus = RunStatus.RUNNING,
    poll_status: RunStatus = RunStatus.COMPLETED,
    output: dict | None = None,
):
    runtime = AsyncMock()
    runtime.name = "mock-docker"
    runtime.start_agent = AsyncMock(
        return_value=AgentRun(
            agent_id=uuid4(),
            status=start_status,
            output_data={"_container": "cairn-mock-abc"},
        )
    )
    runtime.get_run_status = AsyncMock(return_value=poll_status)
    runtime.get_run_output = AsyncMock(return_value=output or {"result": "ok"})
    runtime.cancel_run = AsyncMock()
    runtime.cleanup = AsyncMock()
    return runtime


def _make_security():
    pipeline = AsyncMock()
    pipeline.inspect_outbound = AsyncMock(side_effect=lambda prompt, _: prompt)
    pipeline.inspect_inbound = AsyncMock(side_effect=lambda content: (content, []))
    pipeline.for_agent = lambda _agent: pipeline
    return pipeline


def _make_cred_store():
    store = AsyncMock()
    store.get_credential = AsyncMock(
        return_value=CredentialValue(credential_id="test-key", value="secret-val")
    )
    return store


def _make_conn():
    """Create a mock AsyncConnection."""
    conn = AsyncMock()
    conn.commit = AsyncMock()
    return conn


class TestExecuteHappyPath:
    @pytest.mark.asyncio
    async def test_successful_run(self, agent, pending_run):
        runtime = _make_runtime(
            start_status=RunStatus.RUNNING,
            poll_status=RunStatus.COMPLETED,
            output={"answer": "42"},
        )
        security = _make_security()
        cred_store = _make_cred_store()
        conn = _make_conn()

        service = ExecutionService(runtime, security, cred_store)

        with patch("cairn.execution.service.run_repo") as mock_repo:
            mock_repo.update_status = AsyncMock(return_value=pending_run)
            await service.execute(agent, pending_run, conn)

        # Runtime should have been started and cleaned up.
        runtime.start_agent.assert_called_once()
        runtime.cleanup.assert_called_once()

        # Credentials should have been resolved.
        cred_store.get_credential.assert_called_once()

        # Security middleware should have inspected both directions.
        security.inspect_outbound.assert_called_once()
        security.inspect_inbound.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_credentials(self, agent, pending_run):
        # Agent with no credential references.
        agent = agent.model_copy(update={"credentials": []})
        runtime = _make_runtime()
        security = _make_security()
        conn = _make_conn()

        service = ExecutionService(runtime, security, credential_store=None)

        with patch("cairn.execution.service.run_repo") as mock_repo:
            mock_repo.update_status = AsyncMock(return_value=pending_run)
            await service.execute(agent, pending_run, conn)

        runtime.start_agent.assert_called_once()
        # Credentials list passed to start_agent should be empty.
        _, _, creds = runtime.start_agent.call_args[0]
        assert creds == []


class TestExecuteFailure:
    @pytest.mark.asyncio
    async def test_runtime_start_fails(self, agent, pending_run):
        failed_run = AgentRun(
            agent_id=agent.id,
            status=RunStatus.FAILED,
            error_message="cannot pull image",
        )
        runtime = AsyncMock()
        runtime.start_agent = AsyncMock(return_value=failed_run)
        runtime.cleanup = AsyncMock()
        security = _make_security()
        conn = _make_conn()

        service = ExecutionService(runtime, security)

        with patch("cairn.execution.service.run_repo") as mock_repo:
            mock_repo.update_status = AsyncMock(return_value=pending_run)
            await service.execute(agent, pending_run, conn)

        # Should have updated status to FAILED.
        calls = mock_repo.update_status.call_args_list
        failed_calls = [c for c in calls if c[0][2] == RunStatus.FAILED]
        assert len(failed_calls) >= 1

    @pytest.mark.asyncio
    async def test_exception_during_execution(self, agent, pending_run):
        runtime = AsyncMock()
        runtime.start_agent = AsyncMock(side_effect=RuntimeError("docker exploded"))
        runtime.cleanup = AsyncMock()
        security = _make_security()
        conn = _make_conn()

        service = ExecutionService(runtime, security)

        with patch("cairn.execution.service.run_repo") as mock_repo:
            mock_repo.update_status = AsyncMock(return_value=pending_run)
            await service.execute(agent, pending_run, conn)

        # Cleanup should still be called.
        runtime.cleanup.assert_called_once()

        # Should have recorded the error.
        failed_calls = [
            c for c in mock_repo.update_status.call_args_list
            if len(c[0]) >= 3 and c[0][2] == RunStatus.FAILED
        ]
        assert len(failed_calls) >= 1


class TestSecurityInspection:
    @pytest.mark.asyncio
    async def test_outbound_inspection_called(self, agent, pending_run):
        runtime = _make_runtime()
        security = _make_security()
        conn = _make_conn()

        service = ExecutionService(runtime, security)

        with patch("cairn.execution.service.run_repo") as mock_repo:
            mock_repo.update_status = AsyncMock(return_value=pending_run)
            await service.execute(agent, pending_run, conn)

        security.inspect_outbound.assert_called_once()
        # First arg should be the string representation of input_data.
        call_args = security.inspect_outbound.call_args[0]
        assert "hello" in call_args[0]

    @pytest.mark.asyncio
    async def test_inbound_inspection_called(self, agent, pending_run):
        runtime = _make_runtime(output={"result": "done"})
        security = _make_security()
        conn = _make_conn()

        service = ExecutionService(runtime, security)

        with patch("cairn.execution.service.run_repo") as mock_repo:
            mock_repo.update_status = AsyncMock(return_value=pending_run)
            await service.execute(agent, pending_run, conn)

        security.inspect_inbound.assert_called_once()

    @pytest.mark.asyncio
    async def test_security_warnings_logged(self, agent, pending_run):
        runtime = _make_runtime()
        pipeline = AsyncMock()
        pipeline.inspect_outbound = AsyncMock(side_effect=lambda prompt, _: prompt)
        pipeline.inspect_inbound = AsyncMock(
            return_value=("sanitized", ["possible injection detected"])
        )
        pipeline.for_agent = lambda _agent: pipeline
        conn = _make_conn()

        service = ExecutionService(runtime, pipeline)

        with patch("cairn.execution.service.run_repo") as mock_repo:
            mock_repo.update_status = AsyncMock(return_value=pending_run)
            # Should not raise, just log the warning.
            await service.execute(agent, pending_run, conn)


class TestCredentialResolution:
    @pytest.mark.asyncio
    async def test_credentials_resolved(self, agent, pending_run):
        runtime = _make_runtime()
        security = _make_security()
        cred_store = _make_cred_store()
        conn = _make_conn()

        service = ExecutionService(runtime, security, cred_store)

        with patch("cairn.execution.service.run_repo") as mock_repo:
            mock_repo.update_status = AsyncMock(return_value=pending_run)
            await service.execute(agent, pending_run, conn)

        cred_store.get_credential.assert_called_once()
        ref = cred_store.get_credential.call_args[0][0]
        assert ref.credential_id == "test-key"
        assert ref.env_var_name == "TEST_KEY"
