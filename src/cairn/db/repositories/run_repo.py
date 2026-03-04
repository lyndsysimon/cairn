from datetime import UTC, datetime
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from cairn.models.run import AgentRun, RunStatus


async def create(conn: AsyncConnection, run: AgentRun) -> AgentRun:
    if run.id is None:
        run = run.model_copy(update={"id": uuid4()})
    now = datetime.now(UTC)
    run = run.model_copy(update={"created_at": now})

    dumped = run.model_dump()
    await conn.execute(
        """
        INSERT INTO agent_runs (
            id, agent_id, status, input_data, output_data,
            error_message, started_at, completed_at, created_at
        ) VALUES (
            %(id)s, %(agent_id)s, %(status)s, %(input_data)s, %(output_data)s,
            %(error_message)s, %(started_at)s, %(completed_at)s, %(created_at)s
        )
        """,
        {
            "id": str(run.id),
            "agent_id": str(run.agent_id),
            "status": run.status.value,
            "input_data": (
                Jsonb(dumped["input_data"]) if dumped["input_data"] is not None else None
            ),
            "output_data": (
                Jsonb(dumped["output_data"]) if dumped["output_data"] is not None else None
            ),
            "error_message": run.error_message,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "created_at": run.created_at,
        },
    )
    return run


async def get_by_id(conn: AsyncConnection, run_id: UUID) -> AgentRun | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM agent_runs WHERE id = %s",
            (str(run_id),),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_run(row)


async def list_by_agent(
    conn: AsyncConnection,
    agent_id: UUID,
    status: RunStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AgentRun]:
    async with conn.cursor(row_factory=dict_row) as cur:
        if status is not None:
            await cur.execute(
                "SELECT * FROM agent_runs WHERE agent_id = %s AND status = %s"
                " ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (str(agent_id), status.value, limit, offset),
            )
        else:
            await cur.execute(
                "SELECT * FROM agent_runs WHERE agent_id = %s"
                " ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (str(agent_id), limit, offset),
            )
        rows = await cur.fetchall()
    return [_row_to_run(row) for row in rows]


async def update_status(
    conn: AsyncConnection,
    run_id: UUID,
    status: RunStatus,
    *,
    output_data: dict | None = None,
    error_message: str | None = None,
) -> AgentRun | None:
    now = datetime.now(UTC)
    fields = ["status = %(status)s"]
    params: dict = {"id": str(run_id), "status": status.value}

    if status == RunStatus.RUNNING:
        fields.append("started_at = %(started_at)s")
        params["started_at"] = now
    elif status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
        fields.append("completed_at = %(completed_at)s")
        params["completed_at"] = now

    if output_data is not None:
        fields.append("output_data = %(output_data)s")
        params["output_data"] = Jsonb(output_data)

    if error_message is not None:
        fields.append("error_message = %(error_message)s")
        params["error_message"] = error_message

    await conn.execute(
        f"UPDATE agent_runs SET {', '.join(fields)} WHERE id = %(id)s",
        params,
    )
    return await get_by_id(conn, run_id)


def _row_to_run(row: dict) -> AgentRun:
    return AgentRun(
        id=row["id"],
        agent_id=row["agent_id"],
        status=row["status"],
        input_data=row["input_data"],
        output_data=row["output_data"],
        error_message=row["error_message"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
    )
