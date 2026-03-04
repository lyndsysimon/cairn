from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from cairn.models.agent import AgentStatus
from cairn.models.credential import CredentialReference
from cairn.models.provider import ModelConfig
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


# --- Model Provider schemas ---


class CreateProviderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider_type: str = Field(min_length=1, max_length=100)
    api_base_url: str | None = None
    api_key_credential_id: str | None = None
    models: list[ModelConfig] = Field(default_factory=list)
    is_enabled: bool = True


class UpdateProviderRequest(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    api_base_url: str | None = None
    api_key_credential_id: str | None = None
    models: list[ModelConfig] | None = None
    is_enabled: bool | None = None


class ProviderResponse(BaseModel):
    id: UUID
    name: str
    provider_type: str
    api_base_url: str | None
    api_key_credential_id: str | None
    models: list[ModelConfig]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class ProviderListResponse(BaseModel):
    providers: list[ProviderResponse]
    total: int
