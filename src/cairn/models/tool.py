from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """A tool that agents can use during execution."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    description: str = ""

    is_enabled: bool = True
    is_builtin: bool = False
    is_sandbox_safe: bool = True

    parameters_schema: dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
