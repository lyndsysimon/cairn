from datetime import UTC, datetime
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row


async def create(
    conn: AsyncConnection,
    credential_id: str,
    store_name: str,
    value: str,
) -> dict:
    row_id = uuid4()
    now = datetime.now(UTC)
    await conn.execute(
        """
        INSERT INTO credentials (
            id, credential_id, encrypted_value,
            store_name, created_at, updated_at
        ) VALUES (
            %(id)s, %(credential_id)s, %(encrypted_value)s,
            %(store_name)s, %(created_at)s, %(updated_at)s
        )
        """,
        {
            "id": str(row_id),
            "credential_id": credential_id,
            "encrypted_value": value.encode("utf-8"),
            "store_name": store_name,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {
        "id": row_id,
        "credential_id": credential_id,
        "store_name": store_name,
        "created_at": now,
        "updated_at": now,
    }


async def get_by_id(conn: AsyncConnection, row_id: UUID) -> dict | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, credential_id, store_name,"
            " created_at, updated_at"
            " FROM credentials WHERE id = %s",
            (str(row_id),),
        )
        return await cur.fetchone()


async def get_by_credential_id(conn: AsyncConnection, credential_id: str) -> dict | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, credential_id, store_name, created_at, updated_at"
            " FROM credentials WHERE credential_id = %s",
            (credential_id,),
        )
        return await cur.fetchone()


async def list_all(
    conn: AsyncConnection,
    store_name: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    async with conn.cursor(row_factory=dict_row) as cur:
        if store_name is not None:
            await cur.execute(
                "SELECT id, credential_id, store_name, created_at, updated_at"
                " FROM credentials WHERE store_name = %s"
                " ORDER BY credential_id ASC LIMIT %s OFFSET %s",
                (store_name, limit, offset),
            )
        else:
            await cur.execute(
                "SELECT id, credential_id, store_name, created_at, updated_at"
                " FROM credentials ORDER BY credential_id ASC LIMIT %s OFFSET %s",
                (limit, offset),
            )
        return await cur.fetchall()


async def update_value(conn: AsyncConnection, row_id: UUID, value: str) -> bool:
    now = datetime.now(UTC)
    cur = await conn.execute(
        "UPDATE credentials"
        " SET encrypted_value = %(value)s,"
        " updated_at = %(updated_at)s"
        " WHERE id = %(id)s",
        {
            "id": str(row_id),
            "value": value.encode("utf-8"),
            "updated_at": now,
        },
    )
    return cur.rowcount > 0


async def delete(conn: AsyncConnection, row_id: UUID) -> bool:
    cur = await conn.execute(
        "DELETE FROM credentials WHERE id = %s",
        (str(row_id),),
    )
    return cur.rowcount > 0
