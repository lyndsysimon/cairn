"""Tests for the agent tool registry."""

from unittest.mock import AsyncMock, patch

import pytest

from cairn.llm.base import LLMToolCall
from cairn.models.agent import AgentDefinition
from cairn.models.run import AgentRun, RunStatus
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.trigger import ManualTrigger
from cairn.orchestration.tools import AgentToolRegistry, _agent_name_to_tool_name


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
            tools, agent_map = await registry.get_tool_definitions(conn)

        assert len(tools) == 1
        assert tools[0].name == "search"
        assert "search" in agent_map
        assert "main-orchestrator" not in agent_map

    @pytest.mark.asyncio
    async def test_filters_by_agent_ids(self):
        agent_a = _make_agent("agent-a")
        agent_b = _make_agent("agent-b")
        conn = AsyncMock()

        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)

        with patch("cairn.orchestration.tools.agent_repo") as mock_repo:
            mock_repo.list_all = AsyncMock(return_value=[agent_a, agent_b])
            tools, agent_map = await registry.get_tool_definitions(conn, agent_ids=[agent_a.id])

        assert len(tools) == 1
        assert tools[0].name == "agent-a"

    @pytest.mark.asyncio
    async def test_empty_when_no_agents(self):
        conn = AsyncMock()
        execution_service = AsyncMock()
        registry = AgentToolRegistry(execution_service)

        with patch("cairn.orchestration.tools.agent_repo") as mock_repo:
            mock_repo.list_all = AsyncMock(return_value=[])
            tools, agent_map = await registry.get_tool_definitions(conn)

        assert tools == []
        assert agent_map == {}


class TestExecuteToolCall:
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        agent = _make_agent("search")
        agent_map = {"search": agent}
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
            result = await registry.execute_tool_call(tool_call, agent_map, conn)

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
    async def test_failed_execution(self):
        agent = _make_agent("failing-agent")
        agent_map = {"failing-agent": agent}
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
            result = await registry.execute_tool_call(tool_call, agent_map, conn)

        assert "error" in result
        assert "container crashed" in result["error"]

    @pytest.mark.asyncio
    async def test_exception_during_execution(self):
        agent = _make_agent("error-agent")
        agent_map = {"error-agent": agent}
        tool_call = LLMToolCall(id="tc_1", name="error-agent", input_data={})

        execution_service = AsyncMock()
        execution_service.execute = AsyncMock(side_effect=RuntimeError("boom"))
        conn = AsyncMock()
        conn.commit = AsyncMock()

        registry = AgentToolRegistry(execution_service)

        with patch("cairn.orchestration.tools.run_repo") as mock_run_repo:
            mock_run_repo.create = AsyncMock(return_value=AgentRun(agent_id=agent.id))
            result = await registry.execute_tool_call(tool_call, agent_map, conn)

        assert "error" in result
        assert "boom" in result["error"]
