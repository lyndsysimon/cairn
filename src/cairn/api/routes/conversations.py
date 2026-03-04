"""Conversation API endpoints for the orchestration agent."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from cairn.api.dependencies import get_db_connection, get_orchestration_service
from cairn.api.schemas import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    SendMessageRequest,
    ToolCallResponse,
    ToolResultResponse,
)
from cairn.db.repositories import conversation_repo, message_repo
from cairn.models.conversation import Message
from cairn.orchestration.service import OrchestrationService

router = APIRouter(tags=["conversations"])


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: CreateConversationRequest,
    conn: AsyncConnection = Depends(get_db_connection),
    service: OrchestrationService = Depends(get_orchestration_service),
):
    try:
        conversation = await service.create_conversation(
            conn,
            orchestrator_agent_id=body.orchestrator_agent_id,
            title=body.title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ConversationResponse(
        id=conversation.id,
        orchestrator_agent_id=conversation.orchestrator_agent_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    orchestrator_agent_id: UUID,
    limit: int = 50,
    offset: int = 0,
    conn: AsyncConnection = Depends(get_db_connection),
):
    conversations = await conversation_repo.list_by_orchestrator(
        conn, orchestrator_agent_id, limit=limit, offset=offset
    )
    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c.id,
                orchestrator_agent_id=c.orchestrator_agent_id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ],
        total=len(conversations),
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
):
    conversation = await conversation_repo.get_by_id(conn, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await message_repo.list_by_conversation(conn, conversation_id)
    return ConversationDetailResponse(
        id=conversation.id,
        orchestrator_agent_id=conversation.orchestrator_agent_id,
        title=conversation.title,
        messages=[_message_to_response(m) for m in messages],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
)
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    conn: AsyncConnection = Depends(get_db_connection),
    service: OrchestrationService = Depends(get_orchestration_service),
):
    try:
        assistant_msg = await service.send_message(conn, conversation_id, body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _message_to_response(assistant_msg)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    conn: AsyncConnection = Depends(get_db_connection),
):
    deleted = await conversation_repo.delete(conn, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await conn.commit()


def _message_to_response(msg: Message) -> MessageResponse:
    tool_calls = None
    if msg.tool_calls:
        tool_calls = [
            ToolCallResponse(
                id=tc.id,
                agent_name=tc.agent_name,
                input_data=tc.input_data,
            )
            for tc in msg.tool_calls
        ]

    tool_result = None
    if msg.tool_result:
        tool_result = ToolResultResponse(
            tool_call_id=msg.tool_result.tool_call_id,
            agent_name=msg.tool_result.agent_name,
            output_data=msg.tool_result.output_data,
            error=msg.tool_result.error,
        )

    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role.value,
        content=msg.content,
        tool_calls=tool_calls,
        tool_result=tool_result,
        created_at=msg.created_at,
    )
