from collections.abc import AsyncGenerator

from psycopg import AsyncConnection

from cairn.config import settings
from cairn.credentials.postgres import PostgresCredentialStore
from cairn.db.connection import get_pool
from cairn.execution.service import ExecutionService
from cairn.runtime.docker import DockerRuntimeProvider
from cairn.security.base import PassthroughInspector


async def get_db_connection() -> AsyncGenerator[AsyncConnection]:
    pool = get_pool()
    async with pool.connection() as conn:
        yield conn


def get_execution_service() -> ExecutionService:
    runtime = DockerRuntimeProvider()
    security = PassthroughInspector()
    credential_store = None
    if settings.encryption_key:
        credential_store = PostgresCredentialStore(get_pool(), settings.encryption_key)
    return ExecutionService(
        runtime=runtime, security=security, credential_store=credential_store
    )
