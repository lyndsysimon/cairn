from cairn.models.agent import AgentDefinition, AgentStatus
from cairn.models.credential import CredentialReference
from cairn.models.run import AgentRun, RunStatus
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.trigger import (
    AgentToAgentTrigger,
    ManualTrigger,
    ScheduledTrigger,
    WebhookTrigger,
)


def test_manual_trigger():
    trigger = ManualTrigger()
    assert trigger.type == "manual"
    assert trigger.model_dump() == {"type": "manual"}


def test_scheduled_trigger():
    trigger = ScheduledTrigger(cron_expression="*/15 * * * *")
    assert trigger.type == "scheduled"
    assert trigger.timezone == "UTC"


def test_webhook_trigger():
    trigger = WebhookTrigger(path="/hooks/my-agent")
    assert trigger.type == "webhook"


def test_agent_to_agent_trigger():
    trigger = AgentToAgentTrigger(source_agent_ids=["agent-1", "agent-2"])
    assert trigger.type == "agent_to_agent"
    assert len(trigger.source_agent_ids) == 2


def test_runtime_config():
    config = RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim")
    assert config.type == RuntimeType.DOCKER
    assert config.timeout_seconds == 300
    assert config.memory_limit_mb == 512


def test_credential_reference():
    ref = CredentialReference(
        store_name="bitwarden", credential_id="api-key-123", env_var_name="API_KEY"
    )
    assert ref.store_name == "bitwarden"


def test_agent_definition(sample_agent: AgentDefinition):
    assert sample_agent.name == "test-agent"
    assert sample_agent.status == AgentStatus.ACTIVE
    assert sample_agent.id is not None

    dumped = sample_agent.model_dump()
    restored = AgentDefinition(**dumped)
    assert restored.name == sample_agent.name
    assert restored.trigger.type == "manual"


def test_agent_definition_json_roundtrip(sample_agent: AgentDefinition):
    json_str = sample_agent.model_dump_json()
    restored = AgentDefinition.model_validate_json(json_str)
    assert restored.id == sample_agent.id
    assert restored.trigger.type == sample_agent.trigger.type


def test_agent_definition_security_middlewares():
    agent = AgentDefinition(
        name="mw-agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger=ManualTrigger(),
        runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
        security_middlewares=["credential_leak_detector"],
    )
    assert agent.security_middlewares == ["credential_leak_detector"]

    # Default should be empty list
    agent2 = AgentDefinition(
        name="no-mw-agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger=ManualTrigger(),
        runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
    )
    assert agent2.security_middlewares == []


def test_agent_run():
    import uuid

    run = AgentRun(agent_id=uuid.uuid4(), input_data={"query": "test"})
    assert run.status == RunStatus.PENDING
    assert run.output_data is None
    assert run.error_message is None
