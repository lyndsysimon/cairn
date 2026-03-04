from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from cairn.api.dependencies import get_db_connection
from cairn.api.schemas import CreateRunRequest, RunListResponse, RunResponse
from cairn.db.repositories import agent_repo, run_repo
from cairn.models.run import AgentRun, RunStatus

router = APIRouter()


@router.post("/agents/{agent_id}/runs", status_code=201)
async def create_run(
    agent_id: UUID,
    body: CreateRunRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> RunResponse:
    agent = await agent_repo.get_by_id(conn, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    run = AgentRun(agent_id=agent_id, input_data=body.input_data)
    created = await run_repo.create(conn, run)
    await conn.commit()
    return RunResponse(**created.model_dump())


@router.get("/agents/{agent_id}/runs")
async def list_runs(
    agent_id: UUID,
    status: RunStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    conn: AsyncConnection = Depends(get_db_connection),
) -> RunListResponse:
    agent = await agent_repo.get_by_id(conn, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    runs = await run_repo.list_by_agent(conn, agent_id, status=status, limit=limit, offset=offset)
    return RunListResponse(
        runs=[RunResponse(**r.model_dump()) for r in runs],
        total=len(runs),
    )


@router.get("/runs/{run_id}")
async def get_run(
    run_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> RunResponse:
    run = await run_repo.get_by_id(conn, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(**run.model_dump())
