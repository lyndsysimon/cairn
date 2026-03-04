from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class ToolCall(BaseModel):
    """A single tool invocation requested by the LLM."""

    id: str
    agent_name: str
    input_data: dict


class ToolResult(BaseModel):
    """The result of executing a tool (sub-agent)."""

    tool_call_id: str
    agent_name: str
    output_data: dict | None = None
    error: str | None = None


class Message(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID
    role: MessageRole
    content: str = ""
    tool_calls: list[ToolCall] | None = None
    tool_result: ToolResult | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    orchestrator_agent_id: UUID
    title: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
