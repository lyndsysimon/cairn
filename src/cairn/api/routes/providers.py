from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from cairn.api.dependencies import get_credential_store, get_db_connection
from cairn.api.schemas import (
    CreateProviderRequest,
    DiscoverModelsRequest,
    DiscoverModelsResponse,
    ProviderListResponse,
    ProviderResponse,
    UpdateProviderRequest,
)
from cairn.db.repositories import provider_repo
from cairn.models.credential import CredentialReference
from cairn.models.provider import ModelProvider

router = APIRouter()


async def _resolve_api_key(api_key_credential_id: str | None) -> str:
    """Resolve an API key from the credential store."""
    if not api_key_credential_id:
        return ""
    cred_store = get_credential_store()
    if cred_store is None:
        raise HTTPException(
            status_code=500,
            detail="Credential store not configured (no encryption key set)",
        )
    ref = CredentialReference(
        store_name="postgres",
        credential_id=api_key_credential_id,
        env_var_name="",
    )
    cred_val = await cred_store.get_credential(ref)
    return cred_val.value


async def _discover_models_for_type(
    provider_type: str, api_key: str, api_base_url: str | None
) -> DiscoverModelsResponse:
    """Dispatch model discovery to the appropriate provider client."""
    if provider_type == "openrouter":
        from cairn.llm.openrouter import OpenRouterClient

        models = await OpenRouterClient.list_models(api_key=api_key, base_url=api_base_url)
        return DiscoverModelsResponse(models=models)
    raise HTTPException(
        status_code=400,
        detail=f"Model discovery not supported for provider type: {provider_type!r}",
    )


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


# Static route must be defined before the /{provider_id} parameterised routes
# so that FastAPI matches it before trying UUID validation.
@router.post("/providers/discover-models")
async def discover_models_presave(
    body: DiscoverModelsRequest,
) -> DiscoverModelsResponse:
    """Discover available models before saving a provider.

    Resolves the API key from the credential store and queries the
    provider's model listing endpoint.
    """
    api_key = await _resolve_api_key(body.api_key_credential_id)
    return await _discover_models_for_type(body.provider_type, api_key, body.api_base_url)


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


@router.post("/providers/{provider_id}/discover-models")
async def discover_models(
    provider_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> DiscoverModelsResponse:
    """Discover available models for an existing saved provider."""
    provider = await provider_repo.get_by_id(conn, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    api_key = await _resolve_api_key(provider.api_key_credential_id)
    return await _discover_models_for_type(provider.provider_type, api_key, provider.api_base_url)
