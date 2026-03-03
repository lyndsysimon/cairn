from enum import StrEnum

from pydantic import BaseModel, Field


class RuntimeType(StrEnum):
    APPLE_CONTAINER = "apple_container"
    PODMAN = "podman"
    DOCKER = "docker"
    AWS_LAMBDA = "aws_lambda"


class RuntimeConfig(BaseModel):
    type: RuntimeType
    image: str | None = None
    timeout_seconds: int = 300
    memory_limit_mb: int = 512
    environment: dict[str, str] = Field(default_factory=dict)
