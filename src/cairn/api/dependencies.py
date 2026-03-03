from collections.abc import AsyncGenerator

from psycopg import AsyncConnection

from cairn.db.connection import get_pool


async def get_db_connection() -> AsyncGenerator[AsyncConnection]:
    pool = get_pool()
    async with pool.connection() as conn:
        yield conn
