from psycopg_pool import AsyncConnectionPool

_pool: AsyncConnectionPool | None = None


async def create_pool(database_url: str) -> AsyncConnectionPool:
    global _pool
    _pool = AsyncConnectionPool(conninfo=database_url, open=False)
    await _pool.open()
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool
