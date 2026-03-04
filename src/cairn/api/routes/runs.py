from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from psycopg import AsyncConnection

from cairn.api.dependencies import get_db_connection, get_execution_service
from cairn.api.schemas import CreateRunRequest, RunListResponse, RunResponse
from cairn.db.repositories import agent_repo, run_repo
from cairn.execution.service import ExecutionService
from cairn.models.agent import AgentDefinition
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


async def _run_agent(
    agent: AgentDefinition,
    run: AgentRun,
    service: ExecutionService,
) -> None:
    """Background task: execute the agent run in a runtime container."""
    from cairn.db.connection import get_pool

    pool = get_pool()
    async with pool.connection() as conn:
        await service.execute(agent, run, conn)


@router.post("/runs/{run_id}/execute", status_code=202)
async def execute_run(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    conn: AsyncConnection = Depends(get_db_connection),
    service: ExecutionService = Depends(get_execution_service),
) -> RunResponse:
    """Kick off execution for a PENDING run. Returns immediately (202)."""
    run = await run_repo.get_by_id(conn, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != RunStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Run is {run.status}, only pending runs can be executed",
        )

    agent = await agent_repo.get_by_id(conn, run.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    background_tasks.add_task(_run_agent, agent, run, service)
    return RunResponse(**run.model_dump())


@router.post("/runs/{run_id}/cancel", status_code=200)
async def cancel_run(
    run_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
    service: ExecutionService = Depends(get_execution_service),
) -> RunResponse:
    """Cancel a running agent."""
    run = await run_repo.get_by_id(conn, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail=f"Run is {run.status}, only running runs can be cancelled",
        )

    await service._runtime.cancel_run(run)
    updated = await run_repo.update_status(conn, run_id, RunStatus.CANCELLED)
    await conn.commit()
    return RunResponse(**updated.model_dump())


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
