"""Repository for schedule state tracking.

Tracks when each scheduled agent last fired to prevent duplicate runs
and survive process restarts.
"""

from datetime import UTC, datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import dict_row


async def get_last_scheduled_at(conn: AsyncConnection, agent_id: UUID) -> datetime | None:
    """Return the last_scheduled_at timestamp for an agent, or None if never scheduled."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT last_scheduled_at FROM schedule_state WHERE agent_id = %s",
            (str(agent_id),),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return row["last_scheduled_at"]


async def upsert_last_scheduled_at(
    conn: AsyncConnection, agent_id: UUID, fired_at: datetime
) -> None:
    """Insert or update the last_scheduled_at timestamp for an agent."""
    now = datetime.now(UTC)
    await conn.execute(
        """
        INSERT INTO schedule_state (agent_id, last_scheduled_at, updated_at)
        VALUES (%(agent_id)s, %(fired_at)s, %(now)s)
        ON CONFLICT (agent_id)
        DO UPDATE SET
            last_scheduled_at = %(fired_at)s,
            updated_at = %(now)s
        """,
        {
            "agent_id": str(agent_id),
            "fired_at": fired_at,
            "now": now,
        },
    )


async def delete_for_agent(conn: AsyncConnection, agent_id: UUID) -> None:
    """Remove schedule state for an agent."""
    await conn.execute(
        "DELETE FROM schedule_state WHERE agent_id = %s",
        (str(agent_id),),
    )
