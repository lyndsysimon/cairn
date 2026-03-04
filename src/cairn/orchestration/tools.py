"""Tool framework for the orchestration agent.

Converts sub-agent definitions into LLM tool definitions and executes
tool calls by delegating to the ExecutionService.
"""

import logging
from uuid import UUID

from psycopg import AsyncConnection

from cairn.db.repositories import agent_repo, run_repo
from cairn.execution.service import ExecutionService
from cairn.llm.base import LLMToolCall, ToolDefinition
from cairn.models.agent import AgentDefinition, AgentStatus
from cairn.models.run import AgentRun, RunStatus

logger = logging.getLogger(__name__)


class AgentToolRegistry:
    """Builds LLM tool definitions from available sub-agents and executes tool calls."""

    def __init__(self, execution_service: ExecutionService) -> None:
        self._execution_service = execution_service

    async def get_tool_definitions(
        self,
        conn: AsyncConnection,
        *,
        agent_ids: list[UUID] | None = None,
    ) -> tuple[list[ToolDefinition], dict[str, AgentDefinition]]:
        """Load active sub-agents and return their tool definitions.

        Returns a tuple of (tool definitions for the LLM, name-to-agent mapping).
        If agent_ids is provided, only those agents are included; otherwise
        all active non-orchestrator agents are used.
        """
        agents = await agent_repo.list_all(conn, status=AgentStatus.ACTIVE, limit=200)
        # Filter to non-orchestrator agents
        agents = [a for a in agents if not a.is_orchestrator]

        if agent_ids is not None:
            id_set = set(agent_ids)
            agents = [a for a in agents if a.id in id_set]

        tools = []
        agent_map: dict[str, AgentDefinition] = {}
        for agent in agents:
            tool_name = _agent_name_to_tool_name(agent.name)
            tools.append(
                ToolDefinition(
                    name=tool_name,
                    description=agent.description or f"Execute the {agent.name} agent",
                    input_schema=agent.input_schema,
                )
            )
            agent_map[tool_name] = agent

        return tools, agent_map

    async def execute_tool_call(
        self,
        tool_call: LLMToolCall,
        agent_map: dict[str, AgentDefinition],
        conn: AsyncConnection,
    ) -> dict:
        """Execute a tool call by running the corresponding sub-agent.

        Returns the agent's output_data dict, or an error dict on failure.
        """
        agent = agent_map.get(tool_call.name)
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
