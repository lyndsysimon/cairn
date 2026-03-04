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
from cairn.db.repositories import agent_repo
from cairn.models.agent import AgentDefinition, AgentStatus

router = APIRouter()


@router.post("/agents", status_code=201)
async def create_agent(
    body: CreateAgentRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> AgentResponse:
    agent = AgentDefinition(**body.model_dump())
    created = await agent_repo.create(conn, agent)
    await conn.commit()
    return AgentResponse(**created.model_dump())


@router.get("/agents")
async def list_agents(
    status: AgentStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    conn: AsyncConnection = Depends(get_db_connection),
) -> AgentListResponse:
    agents = await agent_repo.list_all(conn, status=status, limit=limit, offset=offset)
    return AgentListResponse(
        agents=[AgentResponse(**a.model_dump()) for a in agents],
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
    return AgentResponse(**agent.model_dump())


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
    updated_agent = existing.model_copy(update=updates)
    result = await agent_repo.update(conn, updated_agent)
    await conn.commit()
    return AgentResponse(**result.model_dump())


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> None:
    deleted = await agent_repo.delete(conn, agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    await conn.commit()
