from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from cairn.api.dependencies import get_db_connection
from cairn.api.schemas import (
    AgentListResponse,
    AgentResponse,
    CreateAgentRequest,
    UpdateAgentRequest,
)
from cairn.db.repositories import agent_repo, tool_repo
from cairn.models.agent import AgentDefinition, AgentStatus

router = APIRouter()


async def _agent_response(conn: AsyncConnection, agent: AgentDefinition) -> AgentResponse:
    """Build an AgentResponse with tool_ids populated from the junction table."""
    tool_ids = await tool_repo.get_tool_ids_for_agent(conn, agent.id)
    data = agent.model_dump()
    data["tool_ids"] = tool_ids
    return AgentResponse(**data)


@router.post("/agents", status_code=201)
async def create_agent(
    body: CreateAgentRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> AgentResponse:
    request_data = body.model_dump(exclude={"tool_ids"})
    agent = AgentDefinition(**request_data)
    created = await agent_repo.create(conn, agent)

    if body.tool_ids:
        await tool_repo.set_agent_tools(conn, created.id, body.tool_ids)

    await conn.commit()
    return await _agent_response(conn, created)


@router.get("/agents")
async def list_agents(
    status: AgentStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    conn: AsyncConnection = Depends(get_db_connection),
) -> AgentListResponse:
    agents = await agent_repo.list_all(conn, status=status, limit=limit, offset=offset)
    responses = [await _agent_response(conn, a) for a in agents]
    return AgentListResponse(
        agents=responses,
        total=len(agents),
    )


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> AgentResponse:
    agent = await agent_repo.get_by_id(conn, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await _agent_response(conn, agent)


@router.put("/agents/{agent_id}")
async def update_agent(
    agent_id: UUID,
    body: UpdateAgentRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> AgentResponse:
    existing = await agent_repo.get_by_id(conn, agent_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    updates = body.model_dump(exclude_unset=True)
    tool_ids = updates.pop("tool_ids", None)

    updated_agent = existing.model_copy(update=updates)
    result = await agent_repo.update(conn, updated_agent)

    if tool_ids is not None:
        await tool_repo.set_agent_tools(conn, agent_id, tool_ids)

    await conn.commit()
    return await _agent_response(conn, result)


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> None:
    deleted = await agent_repo.delete(conn, agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    await conn.commit()
