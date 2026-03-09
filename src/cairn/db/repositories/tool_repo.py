from datetime import UTC, datetime
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from cairn.models.tool import ToolDefinition


async def create(conn: AsyncConnection, tool: ToolDefinition) -> ToolDefinition:
    if tool.id is None:
        tool = tool.model_copy(update={"id": uuid4()})
    now = datetime.now(UTC)
    tool = tool.model_copy(update={"created_at": now, "updated_at": now})

    await conn.execute(
        """
        INSERT INTO tools (
            id, name, display_name, description,
            is_enabled, is_builtin, is_sandbox_safe,
            parameters_schema, created_at, updated_at
        ) VALUES (
            %(id)s, %(name)s, %(display_name)s, %(description)s,
            %(is_enabled)s, %(is_builtin)s, %(is_sandbox_safe)s,
            %(parameters_schema)s, %(created_at)s, %(updated_at)s
        )
        """,
        {
            "id": str(tool.id),
            "name": tool.name,
            "display_name": tool.display_name,
            "description": tool.description,
            "is_enabled": tool.is_enabled,
            "is_builtin": tool.is_builtin,
            "is_sandbox_safe": tool.is_sandbox_safe,
            "parameters_schema": Jsonb(tool.parameters_schema),
            "created_at": tool.created_at,
            "updated_at": tool.updated_at,
        },
    )
    return tool


async def get_by_id(conn: AsyncConnection, tool_id: UUID) -> ToolDefinition | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT * FROM tools WHERE id = %s", (str(tool_id),))
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_tool(row)


async def get_by_name(conn: AsyncConnection, name: str) -> ToolDefinition | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT * FROM tools WHERE name = %s", (name,))
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_tool(row)


async def list_all(
    conn: AsyncConnection,
    enabled_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[ToolDefinition]:
    async with conn.cursor(row_factory=dict_row) as cur:
        if enabled_only:
            await cur.execute(
                "SELECT * FROM tools WHERE is_enabled = true"
                " ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
        else:
            await cur.execute(
                "SELECT * FROM tools ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
        rows = await cur.fetchall()
    return [_row_to_tool(row) for row in rows]


async def count(conn: AsyncConnection, enabled_only: bool = False) -> int:
    async with conn.cursor(row_factory=dict_row) as cur:
        if enabled_only:
            await cur.execute("SELECT COUNT(*) AS cnt FROM tools WHERE is_enabled = true")
        else:
            await cur.execute("SELECT COUNT(*) AS cnt FROM tools")
        row = await cur.fetchone()
    return row["cnt"] if row else 0


async def update(conn: AsyncConnection, tool: ToolDefinition) -> ToolDefinition:
    now = datetime.now(UTC)
    tool = tool.model_copy(update={"updated_at": now})

    await conn.execute(
        """
        UPDATE tools SET
            display_name = %(display_name)s,
            description = %(description)s,
            is_enabled = %(is_enabled)s,
            is_sandbox_safe = %(is_sandbox_safe)s,
            parameters_schema = %(parameters_schema)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s
        """,
        {
            "id": str(tool.id),
            "display_name": tool.display_name,
            "description": tool.description,
            "is_enabled": tool.is_enabled,
            "is_sandbox_safe": tool.is_sandbox_safe,
            "parameters_schema": Jsonb(tool.parameters_schema),
            "updated_at": tool.updated_at,
        },
    )
    return tool


async def delete(conn: AsyncConnection, tool_id: UUID) -> bool:
    cur = await conn.execute(
        "DELETE FROM tools WHERE id = %s AND is_builtin = false",
        (str(tool_id),),
    )
    return cur.rowcount > 0


async def get_tools_for_agent(conn: AsyncConnection, agent_id: UUID) -> list[ToolDefinition]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            """
            SELECT t.* FROM tools t
            JOIN agent_tools at ON t.id = at.tool_id
            WHERE at.agent_id = %s
            ORDER BY t.name
            """,
            (str(agent_id),),
        )
        rows = await cur.fetchall()
    return [_row_to_tool(row) for row in rows]


async def get_tool_ids_for_agent(conn: AsyncConnection, agent_id: UUID) -> list[UUID]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT tool_id FROM agent_tools WHERE agent_id = %s",
            (str(agent_id),),
        )
        rows = await cur.fetchall()
    return [row["tool_id"] for row in rows]


async def set_agent_tools(conn: AsyncConnection, agent_id: UUID, tool_ids: list[UUID]) -> None:
    await conn.execute(
        "DELETE FROM agent_tools WHERE agent_id = %s",
        (str(agent_id),),
    )
    for tool_id in tool_ids:
        await conn.execute(
            "INSERT INTO agent_tools (agent_id, tool_id) VALUES (%s, %s)",
            (str(agent_id), str(tool_id)),
        )


def _row_to_tool(row: dict) -> ToolDefinition:
    return ToolDefinition(
        id=row["id"],
        name=row["name"],
        display_name=row["display_name"],
        description=row["description"],
        is_enabled=row["is_enabled"],
        is_builtin=row["is_builtin"],
        is_sandbox_safe=row["is_sandbox_safe"],
        parameters_schema=row["parameters_schema"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
