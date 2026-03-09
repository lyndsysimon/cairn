from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from cairn.api.dependencies import get_db_connection
from cairn.api.schemas import (
    CreateToolRequest,
    ToolListResponse,
    ToolResponse,
    UpdateToolRequest,
)
from cairn.db.repositories import tool_repo
from cairn.models.tool import ToolDefinition

router = APIRouter()


@router.post("/tools", status_code=201)
async def create_tool(
    body: CreateToolRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> ToolResponse:
    existing = await tool_repo.get_by_name(conn, body.name)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Tool '{body.name}' already exists",
        )
    tool = ToolDefinition(**body.model_dump())
    created = await tool_repo.create(conn, tool)
    await conn.commit()
    return ToolResponse(**created.model_dump())


@router.get("/tools")
async def list_tools(
    enabled_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    conn: AsyncConnection = Depends(get_db_connection),
) -> ToolListResponse:
    tools = await tool_repo.list_all(conn, enabled_only=enabled_only, limit=limit, offset=offset)
    total = await tool_repo.count(conn, enabled_only=enabled_only)
    return ToolListResponse(
        tools=[ToolResponse(**t.model_dump()) for t in tools],
        total=total,
    )


@router.get("/tools/{tool_id}")
async def get_tool(
    tool_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> ToolResponse:
    tool = await tool_repo.get_by_id(conn, tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return ToolResponse(**tool.model_dump())


@router.put("/tools/{tool_id}")
async def update_tool(
    tool_id: UUID,
    body: UpdateToolRequest,
    conn: AsyncConnection = Depends(get_db_connection),
) -> ToolResponse:
    existing = await tool_repo.get_by_id(conn, tool_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    updates = body.model_dump(exclude_unset=True)

    # Don't allow changing is_sandbox_safe on builtin tools
    if existing.is_builtin and "is_sandbox_safe" in updates:
        raise HTTPException(
            status_code=400,
            detail="Cannot change is_sandbox_safe on built-in tools",
        )

    updated_tool = existing.model_copy(update=updates)
    result = await tool_repo.update(conn, updated_tool)
    await conn.commit()
    return ToolResponse(**result.model_dump())


@router.delete("/tools/{tool_id}", status_code=204)
async def delete_tool(
    tool_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
) -> None:
    existing = await tool_repo.get_by_id(conn, tool_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    if existing.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in tools")
    deleted = await tool_repo.delete(conn, tool_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tool not found")
    await conn.commit()
