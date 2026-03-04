from datetime import UTC, datetime
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from cairn.models.provider import ModelProvider


async def create(conn: AsyncConnection, provider: ModelProvider) -> ModelProvider:
    if provider.id is None:
        provider = provider.model_copy(update={"id": uuid4()})
    now = datetime.now(UTC)
    provider = provider.model_copy(update={"created_at": now, "updated_at": now})

    dumped = provider.model_dump()
    await conn.execute(
        """
        INSERT INTO model_providers (
            id, name, provider_type, api_base_url,
            api_key_credential_id, models, is_enabled,
            created_at, updated_at
        ) VALUES (
            %(id)s, %(name)s, %(provider_type)s, %(api_base_url)s,
            %(api_key_credential_id)s, %(models)s, %(is_enabled)s,
            %(created_at)s, %(updated_at)s
        )
        """,
        {
            "id": str(provider.id),
            "name": provider.name,
            "provider_type": provider.provider_type,
            "api_base_url": provider.api_base_url,
            "api_key_credential_id": provider.api_key_credential_id,
            "models": Jsonb(dumped["models"]),
            "is_enabled": provider.is_enabled,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at,
        },
    )
    return provider


async def get_by_id(conn: AsyncConnection, provider_id: UUID) -> ModelProvider | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT * FROM model_providers WHERE id = %s",
            (str(provider_id),),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_provider(row)


async def list_all(
    conn: AsyncConnection,
    enabled_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[ModelProvider]:
    async with conn.cursor(row_factory=dict_row) as cur:
        if enabled_only:
            await cur.execute(
                "SELECT * FROM model_providers WHERE is_enabled = true"
                " ORDER BY name ASC LIMIT %s OFFSET %s",
                (limit, offset),
            )
        else:
            await cur.execute(
                "SELECT * FROM model_providers ORDER BY name ASC LIMIT %s OFFSET %s",
                (limit, offset),
            )
        rows = await cur.fetchall()
    return [_row_to_provider(row) for row in rows]


async def update(conn: AsyncConnection, provider: ModelProvider) -> ModelProvider:
    now = datetime.now(UTC)
    provider = provider.model_copy(update={"updated_at": now})

    dumped = provider.model_dump()
    await conn.execute(
        """
        UPDATE model_providers SET
            name = %(name)s,
            provider_type = %(provider_type)s,
            api_base_url = %(api_base_url)s,
            api_key_credential_id = %(api_key_credential_id)s,
            models = %(models)s,
            is_enabled = %(is_enabled)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s
        """,
        {
            "id": str(provider.id),
            "name": provider.name,
            "provider_type": provider.provider_type,
            "api_base_url": provider.api_base_url,
            "api_key_credential_id": provider.api_key_credential_id,
            "models": Jsonb(dumped["models"]),
            "is_enabled": provider.is_enabled,
            "updated_at": provider.updated_at,
        },
    )
    return provider


async def delete(conn: AsyncConnection, provider_id: UUID) -> bool:
    cur = await conn.execute(
        "DELETE FROM model_providers WHERE id = %s",
        (str(provider_id),),
    )
    return cur.rowcount > 0


def _row_to_provider(row: dict) -> ModelProvider:
    return ModelProvider(
        id=row["id"],
        name=row["name"],
        provider_type=row["provider_type"],
        api_base_url=row["api_base_url"],
        api_key_credential_id=row["api_key_credential_id"],
        models=row["models"],
        is_enabled=row["is_enabled"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
