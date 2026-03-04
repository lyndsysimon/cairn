from enum import StrEnum
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from croniter import croniter
from pydantic import BaseModel, Field, field_validator


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

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, v: str) -> str:
        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: {v!r}")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (KeyError, ValueError):
            raise ValueError(f"Invalid timezone: {v!r}")
        return v


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
