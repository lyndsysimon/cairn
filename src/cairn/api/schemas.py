from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from cairn.models.agent import AgentStatus
from cairn.models.credential import CredentialReference
from cairn.models.runtime import RuntimeConfig
from cairn.models.trigger import TriggerConfig


class CreateAgentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    model_provider: str
    model_name: str
    system_prompt: str = ""
    input_schema: dict
    output_schema: dict
    trigger: TriggerConfig
    runtime: RuntimeConfig
    credentials: list[CredentialReference] = Field(default_factory=list)


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    system_prompt: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    trigger: TriggerConfig | None = None
    runtime: RuntimeConfig | None = None
    credentials: list[CredentialReference] | None = None
    status: AgentStatus | None = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    description: str
    model_provider: str
    model_name: str
    system_prompt: str
    input_schema: dict
    output_schema: dict
    trigger: TriggerConfig
    runtime: RuntimeConfig
    credentials: list[CredentialReference]
    status: AgentStatus
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int
