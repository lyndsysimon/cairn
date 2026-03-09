"""Tests for built-in tool executors."""

import pytest

from cairn.orchestration.builtin_tools import BUILTIN_EXECUTORS, BashToolExecutor


class TestBashToolExecutor:
    @pytest.mark.asyncio
    async def test_simple_command(self):
        executor = BashToolExecutor()
        result = await executor.execute({"command": "echo hello"})

        assert result["exit_code"] == 0
        assert result["stdout"].strip() == "hello"
        assert result["stderr"] == ""

    @pytest.mark.asyncio
    async def test_command_with_stderr(self):
        executor = BashToolExecutor()
        result = await executor.execute({"command": "echo err >&2"})

        assert result["exit_code"] == 0
        assert result["stderr"].strip() == "err"

    @pytest.mark.asyncio
    async def test_failing_command(self):
        executor = BashToolExecutor()
        result = await executor.execute({"command": "exit 42"})

        assert result["exit_code"] == 42

    @pytest.mark.asyncio
    async def test_missing_command(self):
        executor = BashToolExecutor()
        result = await executor.execute({})

        assert "error" in result
        assert "command" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_timeout(self):
        executor = BashToolExecutor(timeout=1)
        result = await executor.execute({"command": "sleep 10"})

        assert "error" in result
        assert "timed out" in result["error"].lower()


class TestBuiltinExecutorsRegistry:
    def test_bash_registered(self):
        assert "bash" in BUILTIN_EXECUTORS
        assert isinstance(BUILTIN_EXECUTORS["bash"], BashToolExecutor)
