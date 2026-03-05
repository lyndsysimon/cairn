from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

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
    security_middlewares: list[str] = Field(default_factory=list)
    is_orchestrator: bool = False


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
    security_middlewares: list[str] | None = None
    is_orchestrator: bool | None = None
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
    security_middlewares: list[str]
    is_orchestrator: bool
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


DISCOVERABLE_PROVIDER_TYPES: frozenset[str] = frozenset({"openrouter"})


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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def supports_model_discovery(self) -> bool:
        return self.provider_type in DISCOVERABLE_PROVIDER_TYPES


class ProviderListResponse(BaseModel):
    providers: list[ProviderResponse]
    total: int


class DiscoverModelsRequest(BaseModel):
    provider_type: str
    api_base_url: str | None = None
    api_key_credential_id: str | None = None


class DiscoverModelsResponse(BaseModel):
    models: list[ModelConfig]


# --- Credential schemas ---


class CreateCredentialRequest(BaseModel):
    credential_id: str = Field(min_length=1, max_length=255)
    store_name: str = "postgres"
    value: str = Field(min_length=1)


class UpdateCredentialRequest(BaseModel):
    value: str = Field(min_length=1)


class CredentialResponse(BaseModel):
    id: UUID
    credential_id: str
    store_name: str
    created_at: datetime
    updated_at: datetime


class CredentialListResponse(BaseModel):
    credentials: list[CredentialResponse]
    total: int


# --- Agent Run schemas ---


class CreateRunRequest(BaseModel):
    input_data: dict | None = None


class RunResponse(BaseModel):
    id: UUID
    agent_id: UUID
    status: str
    input_data: dict | None
    output_data: dict | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class RunListResponse(BaseModel):
    runs: list[RunResponse]
    total: int


# --- Conversation schemas ---


class CreateConversationRequest(BaseModel):
    orchestrator_agent_id: UUID
    title: str = ""


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1)


class ToolCallResponse(BaseModel):
    id: str
    agent_name: str
    input_data: dict


class ToolResultResponse(BaseModel):
    tool_call_id: str
    agent_name: str
    output_data: dict | None
    error: str | None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    tool_calls: list[ToolCallResponse] | None
    tool_result: ToolResultResponse | None
    created_at: datetime


class ConversationResponse(BaseModel):
    id: UUID
    orchestrator_agent_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    id: UUID
    orchestrator_agent_id: UUID
    title: str
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
