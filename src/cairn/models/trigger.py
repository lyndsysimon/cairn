from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class TriggerType(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    AGENT_TO_AGENT = "agent_to_agent"


class ManualTrigger(BaseModel):
    type: Literal["manual"] = "manual"


class ScheduledTrigger(BaseModel):
    type: Literal["scheduled"] = "scheduled"
    cron_expression: str
    timezone: str = "UTC"


class WebhookTrigger(BaseModel):
    type: Literal["webhook"] = "webhook"
    path: str


class AgentToAgentTrigger(BaseModel):
    type: Literal["agent_to_agent"] = "agent_to_agent"
    source_agent_ids: list[str] = Field(default_factory=list)


TriggerConfig = Annotated[
    ManualTrigger | ScheduledTrigger | WebhookTrigger | AgentToAgentTrigger,
    Field(discriminator="type"),
]
