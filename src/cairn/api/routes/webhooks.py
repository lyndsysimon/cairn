"""Route for receiving inbound webhooks and triggering agent runs."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from psycopg import AsyncConnection

from cairn.api.dependencies import get_db_connection, get_execution_service
from cairn.api.schemas import RunResponse
from cairn.db.repositories import agent_repo, run_repo
from cairn.execution.service import ExecutionService
from cairn.models.run import AgentRun

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_agent(
    agent,
    run: AgentRun,
    service: ExecutionService,
) -> None:
    """Background task: execute the agent run in a runtime container."""
    from cairn.db.connection import get_pool

    pool = get_pool()
    async with pool.connection() as conn:
        await service.execute(agent, run, conn)


@router.post("/webhooks/{path:path}", status_code=202)
async def receive_webhook(
    path: str,
    request: Request,
    background_tasks: BackgroundTasks,
    conn: AsyncConnection = Depends(get_db_connection),
    service: ExecutionService = Depends(get_execution_service),
) -> RunResponse:
    """Receive an inbound webhook and trigger the matching agent.

    Looks up an active agent whose WebhookTrigger path matches the URL path,
    creates a new run with the request body as input data, and kicks off
    execution in the background. Returns 202 immediately.
    """
    agent = await agent_repo.get_by_webhook_path(conn, f"/{path}")
    if agent is None:
        raise HTTPException(status_code=404, detail="No agent registered for this webhook path")

    body = await request.body()
    input_data: dict | None = None
    if body:
        try:
            input_data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Request body is not valid JSON")

    run = AgentRun(agent_id=agent.id, input_data=input_data)
    run = await run_repo.create(conn, run)
    await conn.commit()

    logger.info(
        "Webhook triggered run %s for agent %s (%s) on path /%s",
        run.id,
        agent.id,
        agent.name,
        path,
    )

    background_tasks.add_task(_run_agent, agent, run, service)
    return RunResponse(**run.model_dump())
