"""Tests for SecurityPipeline."""

import pytest

from cairn.models.agent import AgentDefinition
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.trigger import ManualTrigger
from cairn.security.base import SecurityPipeline


def _make_agent(**overrides) -> AgentDefinition:
    defaults = dict(
        name="test-agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger=ManualTrigger(),
        runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
    )
    defaults.update(overrides)
    return AgentDefinition(**defaults)


class _UpperMiddleware:
    """Test middleware that uppercases outbound prompts."""

    async def inspect_outbound(self, prompt: str, credential_values: list[str]) -> str:
        return prompt.upper()

    async def inspect_inbound(self, content: str) -> tuple[str, list[str]]:
        return content, []


class _WarningMiddleware:
    """Test middleware that always emits a warning on inbound."""

    async def inspect_outbound(self, prompt: str, credential_values: list[str]) -> str:
        return prompt

    async def inspect_inbound(self, content: str) -> tuple[str, list[str]]:
        return content, ["test warning"]


class _ReplaceMiddleware:
    """Test middleware that replaces 'foo' with 'bar' outbound and warns inbound."""

    async def inspect_outbound(self, prompt: str, credential_values: list[str]) -> str:
        return prompt.replace("foo", "bar")

    async def inspect_inbound(self, content: str) -> tuple[str, list[str]]:
        return content.replace("foo", "bar"), ["replaced foo"]


class TestEmptyPipeline:
    async def test_outbound_passthrough(self):
        pipeline = SecurityPipeline()
        result = await pipeline.inspect_outbound("hello", ["secret"])
        assert result == "hello"

    async def test_inbound_passthrough(self):
        pipeline = SecurityPipeline()
        content, warnings = await pipeline.inspect_inbound("response data")
        assert content == "response data"
        assert warnings == []


class TestSingleMiddleware:
    async def test_outbound(self):
        pipeline = SecurityPipeline(middlewares=[_UpperMiddleware()])
        result = await pipeline.inspect_outbound("hello", [])
        assert result == "HELLO"

    async def test_inbound(self):
        pipeline = SecurityPipeline(middlewares=[_WarningMiddleware()])
        content, warnings = await pipeline.inspect_inbound("data")
        assert content == "data"
        assert warnings == ["test warning"]


class TestMultipleMiddlewares:
    async def test_outbound_chaining(self):
        pipeline = SecurityPipeline(middlewares=[_ReplaceMiddleware(), _UpperMiddleware()])
        result = await pipeline.inspect_outbound("foo baz", [])
        # First replaces foo→bar, then uppercases
        assert result == "BAR BAZ"

    async def test_inbound_aggregates_warnings(self):
        pipeline = SecurityPipeline(
            middlewares=[_WarningMiddleware(), _ReplaceMiddleware()]
        )
        content, warnings = await pipeline.inspect_inbound("foo data")
        # _WarningMiddleware passes content through; _ReplaceMiddleware replaces foo
        assert content == "bar data"
        assert len(warnings) == 2
        assert "test warning" in warnings
        assert "replaced foo" in warnings


class TestForAgent:
    async def test_combines_platform_and_agent_middlewares(self):
        pipeline = SecurityPipeline(
            middlewares=[_UpperMiddleware()],
            registry={"replace": _ReplaceMiddleware},
        )
        agent = _make_agent(security_middlewares=["replace"])
        agent_pipeline = pipeline.for_agent(agent)

        # Platform uppercases first, then agent replaces (on uppercased text)
        result = await agent_pipeline.inspect_outbound("foo baz", [])
        assert result == "FOO BAZ"  # Uppercased, but "FOO" != "foo" so no replace

    async def test_agent_with_no_extra_middlewares(self):
        pipeline = SecurityPipeline(
            middlewares=[_UpperMiddleware()],
            registry={"replace": _ReplaceMiddleware},
        )
        agent = _make_agent(security_middlewares=[])
        agent_pipeline = pipeline.for_agent(agent)
        result = await agent_pipeline.inspect_outbound("hello", [])
        assert result == "HELLO"

    async def test_unknown_middleware_raises(self):
        pipeline = SecurityPipeline(registry={})
        agent = _make_agent(security_middlewares=["nonexistent"])
        with pytest.raises(ValueError, match="Unknown security middleware"):
            pipeline.for_agent(agent)

    async def test_for_agent_does_not_mutate_original(self):
        pipeline = SecurityPipeline(
            middlewares=[_UpperMiddleware()],
            registry={"warning": _WarningMiddleware},
        )
        agent = _make_agent(security_middlewares=["warning"])

        agent_pipeline = pipeline.for_agent(agent)

        # Original pipeline still has only 1 middleware
        result = await pipeline.inspect_outbound("test", [])
        assert result == "TEST"
        _, warnings = await pipeline.inspect_inbound("data")
        assert warnings == []

        # Agent pipeline has 2
        _, warnings = await agent_pipeline.inspect_inbound("data")
        assert warnings == ["test warning"]


class TestRegister:
    async def test_register_makes_middleware_available(self):
        pipeline = SecurityPipeline()
        pipeline.register("upper", _UpperMiddleware)

        agent = _make_agent(security_middlewares=["upper"])
        agent_pipeline = pipeline.for_agent(agent)
        result = await agent_pipeline.inspect_outbound("hello", [])
        assert result == "HELLO"
