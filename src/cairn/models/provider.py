from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    model_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    is_enabled: bool = True


class ModelProvider(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=255)
    provider_type: str = Field(min_length=1, max_length=100)
    api_base_url: str | None = None
    api_key_credential_id: str | None = None
    models: list[ModelConfig] = Field(default_factory=list)
    is_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
