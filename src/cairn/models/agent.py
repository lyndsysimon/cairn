from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from cairn.models.credential import CredentialReference
from cairn.models.runtime import RuntimeConfig
from cairn.models.trigger import TriggerConfig


class AgentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class AgentDefinition(BaseModel):
    id: UUID = Field(default_factory=uuid4)
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

    status: AgentStatus = AgentStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
