from datetime import UTC, datetime
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from cairn.models.conversation import Conversation


async def create(conn: AsyncConnection, conversation: Conversation) -> Conversation:
    if conversation.id is None:
        conversation = conversation.model_copy(update={"id": uuid4()})
    now = datetime.now(UTC)
    conversation = conversation.model_copy(update={"created_at": now, "updated_at": now})

    await conn.execute(
        """
        INSERT INTO conversations (id, orchestrator_agent_id, title, created_at, updated_at)
        VALUES (%(id)s, %(orchestrator_agent_id)s, %(title)s, %(created_at)s, %(updated_at)s)
        """,
        {
            "id": str(conversation.id),
            "orchestrator_agent_id": str(conversation.orchestrator_agent_id),
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        },
    )
    return conversation


async def get_by_id(conn: AsyncConnection, conversation_id: UUID) -> Conversation | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM conversations WHERE id = %s",
            (str(conversation_id),),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_conversation(row)


async def list_by_orchestrator(
    conn: AsyncConnection,
    orchestrator_agent_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[Conversation]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM conversations WHERE orchestrator_agent_id = %s"
            " ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            (str(orchestrator_agent_id), limit, offset),
        )
        rows = await cur.fetchall()
    return [_row_to_conversation(row) for row in rows]


async def update_title(
    conn: AsyncConnection,
    conversation_id: UUID,
    title: str,
) -> Conversation | None:
    now = datetime.now(UTC)
    await conn.execute(
        "UPDATE conversations SET title = %(title)s, updated_at = %(updated_at)s"
        " WHERE id = %(id)s",
        {"id": str(conversation_id), "title": title, "updated_at": now},
    )
    return await get_by_id(conn, conversation_id)


async def touch(conn: AsyncConnection, conversation_id: UUID) -> None:
    """Update the updated_at timestamp."""
    now = datetime.now(UTC)
    await conn.execute(
        "UPDATE conversations SET updated_at = %s WHERE id = %s",
        (now, str(conversation_id)),
    )


async def delete(conn: AsyncConnection, conversation_id: UUID) -> bool:
    cur = await conn.execute(
        "DELETE FROM conversations WHERE id = %s",
        (str(conversation_id),),
    )
    return cur.rowcount > 0


def _row_to_conversation(row: dict) -> Conversation:
    return Conversation(
        id=row["id"],
        orchestrator_agent_id=row["orchestrator_agent_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
