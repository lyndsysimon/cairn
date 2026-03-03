import pytest
from httpx import ASGITransport, AsyncClient

from cairn.models.agent import AgentDefinition
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.trigger import ManualTrigger


@pytest.fixture
def sample_agent() -> AgentDefinition:
    return AgentDefinition(
        name="test-agent",
        description="A test agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        system_prompt="You are a test agent.",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
        trigger=ManualTrigger(),
        runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
    )


@pytest.fixture
async def client() -> AsyncClient:
    from cairn.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
