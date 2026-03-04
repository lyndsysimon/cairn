from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from cairn.api.dependencies import get_db_connection
from cairn.api.schemas import (
    CreateCredentialRequest,
    CredentialListResponse,
    CredentialResponse,
    UpdateCredentialRequest,
)
from cairn.db.repositories import credential_repo

router = APIRouter()


@router.post("/credentials", status_code=201)
async def create_credential(
    body: CreateCredentialRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> CredentialResponse:
    existing = await credential_repo.get_by_credential_id(conn, body.credential_id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Credential '{body.credential_id}' already exists",
        )
    row = await credential_repo.create(conn, body.credential_id, body.store_name, body.value)
    await conn.commit()
    return CredentialResponse(**row)


@router.get("/credentials")
async def list_credentials(
    store_name: str | None = None,
    limit: int = 50,
    offset: int = 0,
    conn: AsyncConnection = Depends(get_db_connection),
) -> CredentialListResponse:
    rows = await credential_repo.list_all(conn, store_name=store_name, limit=limit, offset=offset)
    return CredentialListResponse(
        credentials=[CredentialResponse(**r) for r in rows],
        total=len(rows),
    )


@router.get("/credentials/{credential_id}")
async def get_credential(
    credential_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> CredentialResponse:
    row = await credential_repo.get_by_id(conn, credential_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    return CredentialResponse(**row)


@router.put("/credentials/{credential_id}")
async def update_credential(
    credential_id: UUID,
    body: UpdateCredentialRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> CredentialResponse:
    row = await credential_repo.get_by_id(conn, credential_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    await credential_repo.update_value(conn, credential_id, body.value)
    await conn.commit()
    updated = await credential_repo.get_by_id(conn, credential_id)
    return CredentialResponse(**updated)


@router.delete("/credentials/{credential_id}", status_code=204)
async def delete_credential(
    credential_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> None:
    deleted = await credential_repo.delete(conn, credential_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credential not found")
    await conn.commit()
