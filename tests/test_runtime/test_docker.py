"""Tests for the Docker runtime provider.

These tests mock asyncio.create_subprocess_exec so they run without Docker.
"""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from cairn.models.agent import AgentDefinition
from cairn.models.credential import CredentialReference, CredentialValue
from cairn.models.run import AgentRun, RunStatus
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.trigger import ManualTrigger
from cairn.runtime.docker import DockerRuntimeProvider


@pytest.fixture
def provider() -> DockerRuntimeProvider:
    return DockerRuntimeProvider()


@pytest.fixture
def agent() -> AgentDefinition:
    return AgentDefinition(
        name="test-agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger=ManualTrigger(),
        runtime=RuntimeConfig(
            type=RuntimeType.DOCKER,
            image="python:3.13-slim",
            timeout_seconds=60,
            memory_limit_mb=256,
        ),
        credentials=[
            CredentialReference(
                store_name="postgres",
                credential_id="my-api-key",
                env_var_name="API_KEY",
            )
        ],
    )


def _make_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""):
    """Create a mock subprocess result."""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


class TestDockerRuntimeProviderName:
    def test_name(self, provider: DockerRuntimeProvider):
        assert provider.name == "docker"


class TestStartAgent:
    @pytest.mark.asyncio
    async def test_start_success(self, provider, agent):
        proc = _make_proc(returncode=0, stdout=b"container_id_abc\n")
        with patch("cairn.runtime.docker.asyncio.create_subprocess_exec", return_value=proc):
            run = await provider.start_agent(agent, {"query": "hello"}, [])

        assert run.status == RunStatus.RUNNING
        assert run.agent_id == agent.id
        assert run.output_data is not None
        assert "_container" in run.output_data
        assert run.output_data["_container"].startswith("cairn-")

    @pytest.mark.asyncio
    async def test_start_failure(self, provider, agent):
        proc = _make_proc(returncode=1, stderr=b"image not found")
        with patch("cairn.runtime.docker.asyncio.create_subprocess_exec", return_value=proc):
            run = await provider.start_agent(agent, {}, [])

        assert run.status == RunStatus.FAILED
        assert "image not found" in run.error_message

    @pytest.mark.asyncio
    async def test_credentials_injected(self, provider, agent):
        """Verify credential values are passed as env flags."""
        creds = [CredentialValue(credential_id="my-api-key", value="secret-123")]
        proc = _make_proc(returncode=0)

        captured_cmd = []

        async def capture_exec(*args, **kwargs):
            captured_cmd.extend(args)
            return proc

        mock_path = "cairn.runtime.docker.asyncio.create_subprocess_exec"
        with patch(mock_path, side_effect=capture_exec):
            await provider.start_agent(agent, {}, creds)

        cmd_str = " ".join(captured_cmd)
        assert "API_KEY=secret-123" in cmd_str

    @pytest.mark.asyncio
    async def test_input_data_injected(self, provider, agent):
        proc = _make_proc(returncode=0)
        captured_cmd = []

        async def capture_exec(*args, **kwargs):
            captured_cmd.extend(args)
            return proc

        mock_path = "cairn.runtime.docker.asyncio.create_subprocess_exec"
        with patch(mock_path, side_effect=capture_exec):
            await provider.start_agent(agent, {"key": "value"}, [])

        cmd_str = " ".join(captured_cmd)
        assert "CAIRN_INPUT=" in cmd_str
        assert '"key"' in cmd_str


class TestGetRunStatus:
    @pytest.mark.asyncio
    async def test_running(self, provider):
        run = AgentRun(
            agent_id=uuid4(),
            status=RunStatus.RUNNING,
            output_data={"_container": "cairn-test-abc"},
        )
        state = {"Running": True, "ExitCode": 0}
        proc = _make_proc(stdout=json.dumps(state).encode())
        with patch("cairn.runtime.docker.asyncio.create_subprocess_exec", return_value=proc):
            status = await provider.get_run_status(run)
        assert status == RunStatus.RUNNING

    @pytest.mark.asyncio
    async def test_completed(self, provider):
        run = AgentRun(
            agent_id=uuid4(),
            status=RunStatus.RUNNING,
            output_data={"_container": "cairn-test-abc"},
        )
        state = {"Running": False, "ExitCode": 0}
        proc = _make_proc(stdout=json.dumps(state).encode())
        with patch("cairn.runtime.docker.asyncio.create_subprocess_exec", return_value=proc):
            status = await provider.get_run_status(run)
        assert status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_failed_exit_code(self, provider):
        run = AgentRun(
            agent_id=uuid4(),
            status=RunStatus.RUNNING,
            output_data={"_container": "cairn-test-abc"},
        )
        state = {"Running": False, "ExitCode": 1}
        proc = _make_proc(stdout=json.dumps(state).encode())
        with patch("cairn.runtime.docker.asyncio.create_subprocess_exec", return_value=proc):
            status = await provider.get_run_status(run)
        assert status == RunStatus.FAILED

    @pytest.mark.asyncio
    async def test_no_container_metadata(self, provider):
        run = AgentRun(agent_id=uuid4(), status=RunStatus.RUNNING)
        status = await provider.get_run_status(run)
        assert status == RunStatus.FAILED


class TestGetRunOutput:
    @pytest.mark.asyncio
    async def test_json_output(self, provider):
        run = AgentRun(
            agent_id=uuid4(),
            status=RunStatus.COMPLETED,
            output_data={"_container": "cairn-test-abc"},
        )
        output_line = json.dumps({"answer": "42"})
        proc = _make_proc(stdout=f"some log line\n{output_line}\n".encode())
        with patch("cairn.runtime.docker.asyncio.create_subprocess_exec", return_value=proc):
            result = await provider.get_run_output(run)
        assert result == {"answer": "42"}

    @pytest.mark.asyncio
    async def test_raw_output_fallback(self, provider):
        run = AgentRun(
            agent_id=uuid4(),
            status=RunStatus.COMPLETED,
            output_data={"_container": "cairn-test-abc"},
        )
        proc = _make_proc(stdout=b"just plain text output")
        with patch("cairn.runtime.docker.asyncio.create_subprocess_exec", return_value=proc):
            result = await provider.get_run_output(run)
        assert result == {"raw_output": "just plain text output"}

    @pytest.mark.asyncio
    async def test_no_container(self, provider):
        run = AgentRun(agent_id=uuid4(), status=RunStatus.COMPLETED)
        result = await provider.get_run_output(run)
        assert result is None


class TestCancelRun:
    @pytest.mark.asyncio
    async def test_cancel(self, provider):
        run = AgentRun(
            agent_id=uuid4(),
            status=RunStatus.RUNNING,
            output_data={"_container": "cairn-test-abc"},
        )
        proc = _make_proc()
        mock_path = "cairn.runtime.docker.asyncio.create_subprocess_exec"
        with patch(mock_path, return_value=proc) as mock_exec:
            await provider.cancel_run(run)
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert "stop" in args


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup(self, provider):
        run = AgentRun(
            agent_id=uuid4(),
            status=RunStatus.COMPLETED,
            output_data={"_container": "cairn-test-abc"},
        )
        proc = _make_proc()
        mock_path = "cairn.runtime.docker.asyncio.create_subprocess_exec"
        with patch(mock_path, return_value=proc) as mock_exec:
            await provider.cleanup(run)
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert "rm" in args


class TestBuildRunCommand:
    def test_security_flags(self):
        cmd = DockerRuntimeProvider._build_run_command(
            container_name="cairn-test",
            image="python:3.13-slim",
            env_flags=["-e", "FOO=bar"],
            memory_mb=512,
            timeout=300,
        )
        assert "-d" in cmd
        assert "--read-only" in cmd
        assert "--network" in cmd
        assert "none" in cmd
        assert "--name" in cmd
        assert "cairn-test" in cmd
        assert "--memory=512m" in cmd

    def test_env_flags_included(self):
        cmd = DockerRuntimeProvider._build_run_command(
            container_name="cairn-test",
            image="alpine",
            env_flags=["-e", "X=1", "-e", "Y=2"],
            memory_mb=256,
            timeout=60,
        )
        assert "-e" in cmd
        assert "X=1" in cmd
        assert "Y=2" in cmd


class TestBuildEnvFlags:
    def test_input_and_credentials(self):
        agent = AgentDefinition(
            name="test",
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            input_schema={},
            output_schema={},
            trigger=ManualTrigger(),
            runtime=RuntimeConfig(
                type=RuntimeType.DOCKER,
                environment={"STATIC": "value"},
            ),
            credentials=[
                CredentialReference(
                    store_name="postgres",
                    credential_id="key1",
                    env_var_name="KEY_ONE",
                )
            ],
        )
        creds = [CredentialValue(credential_id="key1", value="secret")]
        flags = DockerRuntimeProvider._build_env_flags(agent, {"q": "test"}, creds)

        # Should contain CAIRN_INPUT, STATIC env var, and credential
        flag_str = " ".join(flags)
        assert "CAIRN_INPUT=" in flag_str
        assert "STATIC=value" in flag_str
        assert "KEY_ONE=secret" in flag_str
