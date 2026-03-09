"""Tests for the agent tool registry."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from cairn.llm.base import LLMToolCall
from cairn.models.agent import AgentDefinition
from cairn.models.run import AgentRun, RunStatus
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.tool import ToolDefinition as DBToolDefinition
from cairn.models.trigger import ManualTrigger
from cairn.orchestration.tools import AgentToolRegistry, ToolTarget, _agent_name_to_tool_name


def _make_agent(name: str, is_orchestrator: bool = False) -> AgentDefinition:
    return AgentDefinition(
        name=name,
        description=f"The {name} agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        trigger=ManualTrigger(),
        runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
        is_orchestrator=is_orchestrator,
    )


class TestAgentNameToToolName:
    def test_simple_name(self):
        assert _agent_name_to_tool_name("weather") == "weather"

    def test_name_with_spaces(self):
        assert _agent_name_to_tool_name("weather agent") == "weather_agent"

    def test_name_with_dots(self):
        assert _agent_name_to_tool_name("v2.weather") == "v2_weather"

    def test_hyphenated_name(self):
        assert _agent_name_to_tool_name("web-search") == "web-search"


def _make_db_tool(name: str = "bash", is_builtin: bool = True) -> DBToolDefinition:
    return DBToolDefinition(
        name=name,
        display_name=name.title(),
        description=f"Execute a {name} command.",
        is_enabled=True,
        is_builtin=is_builtin,
        parameters_schema={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    )


class TestGetToolDefinitions:
    @pytest.mark.asyncio
    async def test_returns_active_non_orchestrator_agents(self):
        sub_agent = _make_agent("search")
        orchestrator = _make_agent("main-orchestrator", is_orchestrator=True)
        conn = AsyncMock()

        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)

        with patch("cairn.orchestration.tools.agent_repo") as mock_repo:
            mock_repo.list_all = AsyncMock(return_value=[sub_agent, orchestrator])
            tools, tool_map = await registry.get_tool_definitions(conn)

        assert len(tools) == 1
        assert tools[0].name == "search"
        assert "search" in tool_map
        assert tool_map["search"].kind == "agent"
        assert tool_map["search"].agent == sub_agent
        assert "main-orchestrator" not in tool_map

    @pytest.mark.asyncio
    async def test_filters_by_agent_ids(self):
        agent_a = _make_agent("agent-a")
        agent_b = _make_agent("agent-b")
        conn = AsyncMock()

        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)

        with patch("cairn.orchestration.tools.agent_repo") as mock_repo:
            mock_repo.list_all = AsyncMock(return_value=[agent_a, agent_b])
            tools, tool_map = await registry.get_tool_definitions(conn, agent_ids=[agent_a.id])

        assert len(tools) == 1
        assert tools[0].name == "agent-a"

    @pytest.mark.asyncio
    async def test_empty_when_no_agents(self):
        conn = AsyncMock()
        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)

        with patch("cairn.orchestration.tools.agent_repo") as mock_repo:
            mock_repo.list_all = AsyncMock(return_value=[])
            tools, tool_map = await registry.get_tool_definitions(conn)

        assert tools == []
        assert tool_map == {}

    @pytest.mark.asyncio
    async def test_includes_builtin_tools_for_orchestrator(self):
        conn = AsyncMock()
        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)
        orchestrator_id = uuid4()
        bash_tool = _make_db_tool("bash")

        with (
            patch("cairn.orchestration.tools.agent_repo") as mock_agent_repo,
            patch("cairn.orchestration.tools.tool_repo") as mock_tool_repo,
        ):
            mock_agent_repo.list_all = AsyncMock(return_value=[])
            mock_tool_repo.get_tools_for_agent = AsyncMock(return_value=[bash_tool])

            tools, tool_map = await registry.get_tool_definitions(
                conn, orchestrator_agent_id=orchestrator_id
            )

        assert len(tools) == 1
        assert tools[0].name == "bash"
        assert "bash" in tool_map
        assert tool_map["bash"].kind == "builtin"
        assert tool_map["bash"].builtin_tool == bash_tool

    @pytest.mark.asyncio
    async def test_skips_disabled_builtin_tools(self):
        conn = AsyncMock()
        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)
        orchestrator_id = uuid4()
        disabled_tool = _make_db_tool("bash")
        disabled_tool = disabled_tool.model_copy(update={"is_enabled": False})

        with (
            patch("cairn.orchestration.tools.agent_repo") as mock_agent_repo,
            patch("cairn.orchestration.tools.tool_repo") as mock_tool_repo,
        ):
            mock_agent_repo.list_all = AsyncMock(return_value=[])
            mock_tool_repo.get_tools_for_agent = AsyncMock(return_value=[disabled_tool])

            tools, tool_map = await registry.get_tool_definitions(
                conn, orchestrator_agent_id=orchestrator_id
            )

        assert tools == []
        assert tool_map == {}

    @pytest.mark.asyncio
    async def test_builtin_tool_skipped_on_name_conflict(self):
        """A built-in tool is skipped if a sub-agent already uses that name."""
        conn = AsyncMock()
        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)
        orchestrator_id = uuid4()

        sub_agent = _make_agent("bash")
        bash_tool = _make_db_tool("bash")

        with (
            patch("cairn.orchestration.tools.agent_repo") as mock_agent_repo,
            patch("cairn.orchestration.tools.tool_repo") as mock_tool_repo,
        ):
            mock_agent_repo.list_all = AsyncMock(return_value=[sub_agent])
            mock_tool_repo.get_tools_for_agent = AsyncMock(return_value=[bash_tool])

            tools, tool_map = await registry.get_tool_definitions(
                conn, orchestrator_agent_id=orchestrator_id
            )

        # Only the sub-agent should appear
        assert len(tools) == 1
        assert tool_map["bash"].kind == "agent"


class TestExecuteToolCall:
    @pytest.mark.asyncio
    async def test_successful_agent_execution(self):
        agent = _make_agent("search")
        tool_map = {"search": ToolTarget(kind="agent", agent=agent)}
        tool_call = LLMToolCall(id="tc_1", name="search", input_data={"query": "test"})

        completed_run = AgentRun(
            agent_id=agent.id,
            status=RunStatus.COMPLETED,
            output_data={"result": "found it"},
        )
        execution_service = AsyncMock()
        execution_service.execute = AsyncMock(return_value=completed_run)
        conn = AsyncMock()
        conn.commit = AsyncMock()

        registry = AgentToolRegistry(execution_service)

        with patch("cairn.orchestration.tools.run_repo") as mock_run_repo:
            mock_run_repo.create = AsyncMock(
                return_value=AgentRun(agent_id=agent.id, input_data={"query": "test"})
            )
            result = await registry.execute_tool_call(tool_call, tool_map, conn)

        assert result == {"result": "found it"}

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        tool_call = LLMToolCall(id="tc_1", name="nonexistent", input_data={})
        conn = AsyncMock()
        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)

        result = await registry.execute_tool_call(tool_call, {}, conn)
        assert "error" in result
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_failed_agent_execution(self):
        agent = _make_agent("failing-agent")
        tool_map = {"failing-agent": ToolTarget(kind="agent", agent=agent)}
        tool_call = LLMToolCall(id="tc_1", name="failing-agent", input_data={})

        failed_run = AgentRun(
            agent_id=agent.id,
            status=RunStatus.FAILED,
            error_message="container crashed",
        )
        execution_service = AsyncMock()
        execution_service.execute = AsyncMock(return_value=failed_run)
        conn = AsyncMock()
        conn.commit = AsyncMock()

        registry = AgentToolRegistry(execution_service)

        with patch("cairn.orchestration.tools.run_repo") as mock_run_repo:
            mock_run_repo.create = AsyncMock(return_value=AgentRun(agent_id=agent.id))
            result = await registry.execute_tool_call(tool_call, tool_map, conn)

        assert "error" in result
        assert "container crashed" in result["error"]

    @pytest.mark.asyncio
    async def test_exception_during_agent_execution(self):
        agent = _make_agent("error-agent")
        tool_map = {"error-agent": ToolTarget(kind="agent", agent=agent)}
        tool_call = LLMToolCall(id="tc_1", name="error-agent", input_data={})

        execution_service = AsyncMock()
        execution_service.execute = AsyncMock(side_effect=RuntimeError("boom"))
        conn = AsyncMock()
        conn.commit = AsyncMock()

        registry = AgentToolRegistry(execution_service)

        with patch("cairn.orchestration.tools.run_repo") as mock_run_repo:
            mock_run_repo.create = AsyncMock(return_value=AgentRun(agent_id=agent.id))
            result = await registry.execute_tool_call(tool_call, tool_map, conn)

        assert "error" in result
        assert "boom" in result["error"]

    @pytest.mark.asyncio
    async def test_builtin_tool_execution(self):
        bash_tool = _make_db_tool("bash")
        tool_map = {"bash": ToolTarget(kind="builtin", builtin_tool=bash_tool)}
        tool_call = LLMToolCall(id="tc_1", name="bash", input_data={"command": "echo hello"})

        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)
        conn = AsyncMock()

        result = await registry.execute_tool_call(tool_call, tool_map, conn)

        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
