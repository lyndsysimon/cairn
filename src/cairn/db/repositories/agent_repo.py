from datetime import UTC, datetime
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from cairn.models.agent import AgentDefinition, AgentStatus


async def create(conn: AsyncConnection, agent: AgentDefinition) -> AgentDefinition:
    if agent.id is None:
        agent = agent.model_copy(update={"id": uuid4()})
    now = datetime.now(UTC)
    agent = agent.model_copy(update={"created_at": now, "updated_at": now})

    dumped = agent.model_dump()
    await conn.execute(
        """
        INSERT INTO agents (
            id, name, description, model_provider, model_name,
            system_prompt, input_schema, output_schema,
            trigger_config, runtime_config, credentials,
            security_middlewares, is_orchestrator, status,
            created_at, updated_at
        ) VALUES (
            %(id)s, %(name)s, %(description)s, %(model_provider)s, %(model_name)s,
            %(system_prompt)s, %(input_schema)s, %(output_schema)s,
            %(trigger_config)s, %(runtime_config)s, %(credentials)s,
            %(security_middlewares)s, %(is_orchestrator)s, %(status)s,
            %(created_at)s, %(updated_at)s
        )
        """,
        {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "model_provider": agent.model_provider,
            "model_name": agent.model_name,
            "system_prompt": agent.system_prompt,
            "input_schema": Jsonb(dumped["input_schema"]),
            "output_schema": Jsonb(dumped["output_schema"]),
            "trigger_config": Jsonb(dumped["trigger"]),
            "runtime_config": Jsonb(dumped["runtime"]),
            "credentials": Jsonb(dumped["credentials"]),
            "security_middlewares": Jsonb(dumped["security_middlewares"]),
            "is_orchestrator": agent.is_orchestrator,
            "status": agent.status.value,
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
        },
    )
    return agent


async def get_by_id(conn: AsyncConnection, agent_id: UUID) -> AgentDefinition | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM agents WHERE id = %s",
            (str(agent_id),),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_agent(row)


async def list_all(
    conn: AsyncConnection,
    status: AgentStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AgentDefinition]:
    async with conn.cursor(row_factory=dict_row) as cur:
        if status is not None:
            await cur.execute(
                "SELECT * FROM agents WHERE status = %s"
                " ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (status.value, limit, offset),
            )
        else:
            await cur.execute(
                "SELECT * FROM agents ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
        rows = await cur.fetchall()
    return [_row_to_agent(row) for row in rows]


async def update(conn: AsyncConnection, agent: AgentDefinition) -> AgentDefinition:
    now = datetime.now(UTC)
    agent = agent.model_copy(update={"updated_at": now})

    dumped = agent.model_dump()
    await conn.execute(
        """
        UPDATE agents SET
            name = %(name)s,
            description = %(description)s,
            model_provider = %(model_provider)s,
            model_name = %(model_name)s,
            system_prompt = %(system_prompt)s,
            input_schema = %(input_schema)s,
            output_schema = %(output_schema)s,
            trigger_config = %(trigger_config)s,
            runtime_config = %(runtime_config)s,
            credentials = %(credentials)s,
            security_middlewares = %(security_middlewares)s,
            is_orchestrator = %(is_orchestrator)s,
            status = %(status)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s
        """,
        {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "model_provider": agent.model_provider,
            "model_name": agent.model_name,
            "system_prompt": agent.system_prompt,
            "input_schema": Jsonb(dumped["input_schema"]),
            "output_schema": Jsonb(dumped["output_schema"]),
            "trigger_config": Jsonb(dumped["trigger"]),
            "runtime_config": Jsonb(dumped["runtime"]),
            "credentials": Jsonb(dumped["credentials"]),
            "security_middlewares": Jsonb(dumped["security_middlewares"]),
            "is_orchestrator": agent.is_orchestrator,
            "status": agent.status.value,
            "updated_at": agent.updated_at,
        },
    )
    return agent


async def get_by_webhook_path(conn: AsyncConnection, path: str) -> AgentDefinition | None:
    """Find an active agent whose webhook trigger matches the given path."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM agents"
            " WHERE status = %s"
            "   AND trigger_config->>'type' = 'webhook'"
            "   AND trigger_config->>'path' = %s"
            " LIMIT 1",
            (AgentStatus.ACTIVE.value, path),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_agent(row)


async def delete(conn: AsyncConnection, agent_id: UUID) -> bool:
    cur = await conn.execute(
        "DELETE FROM agents WHERE id = %s",
        (str(agent_id),),
    )
    return cur.rowcount > 0


def _row_to_agent(row: dict) -> AgentDefinition:
    return AgentDefinition(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        model_provider=row["model_provider"],
        model_name=row["model_name"],
        system_prompt=row["system_prompt"],
        input_schema=row["input_schema"],
        output_schema=row["output_schema"],
        trigger=row["trigger_config"],
        runtime=row["runtime_config"],
        credentials=row["credentials"],
        security_middlewares=row.get("security_middlewares", []),
        is_orchestrator=row.get("is_orchestrator", False),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
