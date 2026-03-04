from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from cairn.api.dependencies import get_db_connection
from cairn.api.schemas import (
    CreateProviderRequest,
    ProviderListResponse,
    ProviderResponse,
    UpdateProviderRequest,
)
from cairn.db.repositories import provider_repo
from cairn.models.provider import ModelProvider

router = APIRouter()


@router.post("/providers", status_code=201)
async def create_provider(
    body: CreateProviderRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> ProviderResponse:
    provider = ModelProvider(**body.model_dump())
    created = await provider_repo.create(conn, provider)
    await conn.commit()
    return ProviderResponse(**created.model_dump())


@router.get("/providers")
async def list_providers(
    enabled_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    conn: AsyncConnection = Depends(get_db_connection),
) -> ProviderListResponse:
    providers = await provider_repo.list_all(
        conn, enabled_only=enabled_only, limit=limit, offset=offset
    )
    return ProviderListResponse(
        providers=[ProviderResponse(**p.model_dump()) for p in providers],
        total=len(providers),
    )


@router.get("/providers/{provider_id}")
async def get_provider(
    provider_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> ProviderResponse:
    provider = await provider_repo.get_by_id(conn, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderResponse(**provider.model_dump())


@router.put("/providers/{provider_id}")
async def update_provider(
    provider_id: UUID,
    body: UpdateProviderRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> ProviderResponse:
    existing = await provider_repo.get_by_id(conn, provider_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    updates = body.model_dump(exclude_unset=True)
    updated_provider = existing.model_copy(update=updates)
    result = await provider_repo.update(conn, updated_provider)
    await conn.commit()
    return ProviderResponse(**result.model_dump())


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> None:
    deleted = await provider_repo.delete(conn, provider_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Provider not found")
    await conn.commit()
