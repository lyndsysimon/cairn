from datetime import UTC, datetime
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from cairn.models.conversation import Message, MessageRole, ToolCall, ToolResult


async def create(conn: AsyncConnection, message: Message) -> Message:
    if message.id is None:
        message = message.model_copy(update={"id": uuid4()})
    now = datetime.now(UTC)
    message = message.model_copy(update={"created_at": now})

    dumped = message.model_dump()
    await conn.execute(
        """
        INSERT INTO messages (
            id, conversation_id, role, content,
            tool_calls, tool_result, created_at
        )
        VALUES (
            %(id)s, %(conversation_id)s, %(role)s, %(content)s,
            %(tool_calls)s, %(tool_result)s, %(created_at)s
        )
        """,
        {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "role": message.role.value,
            "content": message.content,
            "tool_calls": Jsonb(dumped["tool_calls"]) if dumped["tool_calls"] else None,
            "tool_result": Jsonb(dumped["tool_result"]) if dumped["tool_result"] else None,
            "created_at": message.created_at,
        },
    )
    return message


async def list_by_conversation(
    conn: AsyncConnection,
    conversation_id: UUID,
    limit: int = 200,
    offset: int = 0,
) -> list[Message]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM messages WHERE conversation_id = %s"
            " ORDER BY created_at ASC LIMIT %s OFFSET %s",
            (str(conversation_id), limit, offset),
        )
        rows = await cur.fetchall()
    return [_row_to_message(row) for row in rows]


async def get_by_id(conn: AsyncConnection, message_id: UUID) -> Message | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM messages WHERE id = %s",
            (str(message_id),),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_message(row)


def _row_to_message(row: dict) -> Message:
    tool_calls = None
    if row.get("tool_calls"):
        tool_calls = [ToolCall(**tc) for tc in row["tool_calls"]]

    tool_result = None
    if row.get("tool_result"):
        tool_result = ToolResult(**row["tool_result"])

    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=MessageRole(row["role"]),
        content=row["content"],
        tool_calls=tool_calls,
        tool_result=tool_result,
        created_at=row["created_at"],
    )
