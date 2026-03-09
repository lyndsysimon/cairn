"""Tool framework for the orchestration agent.

Converts sub-agent definitions and built-in tools into LLM tool definitions,
and executes tool calls by delegating to the appropriate executor.
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from psycopg import AsyncConnection

from cairn.db.repositories import agent_repo, run_repo, tool_repo
from cairn.execution.service import ExecutionService
from cairn.llm.base import LLMToolCall, ToolDefinition
from cairn.models.agent import AgentDefinition, AgentStatus
from cairn.models.run import AgentRun, RunStatus
from cairn.models.tool import ToolDefinition as DBToolDefinition
from cairn.orchestration.builtin_tools import BUILTIN_EXECUTORS

logger = logging.getLogger(__name__)


@dataclass
class ToolTarget:
    """Identifies what a tool name resolves to for execution."""

    kind: str  # "agent" | "builtin"
    agent: AgentDefinition | None = None
    builtin_tool: DBToolDefinition | None = None


class AgentToolRegistry:
    """Builds LLM tool definitions from available sub-agents and built-in tools."""

    def __init__(self, execution_service: ExecutionService) -> None:
        self._execution_service = execution_service

    async def get_tool_definitions(
        self,
        conn: AsyncConnection,
        *,
        orchestrator_agent_id: UUID | None = None,
        agent_ids: list[UUID] | None = None,
    ) -> tuple[list[ToolDefinition], dict[str, ToolTarget]]:
        """Load active sub-agents and built-in tools, returning their tool definitions.

        Returns a tuple of (tool definitions for the LLM, name-to-target mapping).
        If agent_ids is provided, only those agents are included; otherwise
        all active non-orchestrator agents are used.
        If orchestrator_agent_id is provided, built-in tools assigned to that
        agent are also included.
        """
        agents = await agent_repo.list_all(conn, status=AgentStatus.ACTIVE, limit=200)
        # Filter to non-orchestrator agents
        agents = [a for a in agents if not a.is_orchestrator]

        if agent_ids is not None:
            id_set = set(agent_ids)
            agents = [a for a in agents if a.id in id_set]

        tools: list[ToolDefinition] = []
        tool_map: dict[str, ToolTarget] = {}
        for agent in agents:
            tool_name = _agent_name_to_tool_name(agent.name)
            tools.append(
                ToolDefinition(
                    name=tool_name,
                    description=agent.description or f"Execute the {agent.name} agent",
                    input_schema=agent.input_schema,
                )
            )
            tool_map[tool_name] = ToolTarget(kind="agent", agent=agent)

        # Load built-in tools assigned to the orchestrator
        if orchestrator_agent_id is not None:
            agent_tools = await tool_repo.get_tools_for_agent(conn, orchestrator_agent_id)
            for db_tool in agent_tools:
                if not db_tool.is_enabled:
                    continue
                if db_tool.name not in BUILTIN_EXECUTORS:
                    continue
                if db_tool.name in tool_map:
                    logger.warning(
                        "Built-in tool %r skipped: name conflicts with a sub-agent tool",
                        db_tool.name,
                    )
                    continue
                tools.append(
                    ToolDefinition(
                        name=db_tool.name,
                        description=db_tool.description,
                        input_schema=db_tool.parameters_schema,
                    )
                )
                tool_map[db_tool.name] = ToolTarget(kind="builtin", builtin_tool=db_tool)

        return tools, tool_map

    async def execute_tool_call(
        self,
        tool_call: LLMToolCall,
        tool_map: dict[str, ToolTarget],
        conn: AsyncConnection,
    ) -> dict:
        """Execute a tool call by dispatching to the appropriate executor.

        Returns the tool's output dict, or an error dict on failure.
        """
        target = tool_map.get(tool_call.name)
        if target is None:
            return {"error": f"Unknown tool: {tool_call.name}"}

        if target.kind == "builtin":
            executor = BUILTIN_EXECUTORS.get(tool_call.name)
            if executor is None:
                return {"error": f"No executor for built-in tool: {tool_call.name}"}
            logger.info("Executing built-in tool %s (call %s)", tool_call.name, tool_call.id)
            return await executor.execute(tool_call.input_data)

        # Sub-agent execution
        agent = target.agent
        if agent is None:
            return {"error": f"Unknown tool: {tool_call.name}"}

        logger.info(
            "Executing tool call %s -> agent %s (%s)",
            tool_call.id,
            agent.name,
            agent.id,
        )

        run = AgentRun(agent_id=agent.id, input_data=tool_call.input_data)

        try:
            run = await run_repo.create(conn, run)
            await conn.commit()

            result = await self._execution_service.execute(agent, run, conn)

            if result.status == RunStatus.COMPLETED and result.output_data:
                return result.output_data
            elif result.status == RunStatus.FAILED:
                return {"error": result.error_message or "Agent execution failed"}
            else:
                return {"error": f"Agent finished with status: {result.status}"}

        except Exception as exc:
            logger.exception("Tool call %s failed", tool_call.id)
            return {"error": str(exc)}


def _agent_name_to_tool_name(name: str) -> str:
    """Convert an agent name to a valid tool name.

    Tool names must match [a-zA-Z0-9_-]+ for the Anthropic API.
    """
    return name.replace(" ", "_").replace(".", "_")
