"""Tests for conversation and message models."""

from uuid import uuid4

from cairn.models.conversation import (
    Conversation,
    Message,
    MessageRole,
    ToolCall,
    ToolResult,
)


class TestConversation:
    def test_defaults(self):
        conv = Conversation(orchestrator_agent_id=uuid4())
        assert conv.id is not None
        assert conv.title == ""
        assert conv.created_at is not None

    def test_with_title(self):
        conv = Conversation(orchestrator_agent_id=uuid4(), title="My chat")
        assert conv.title == "My chat"


class TestMessage:
    def test_user_message(self):
        conv_id = uuid4()
        msg = Message(
            conversation_id=conv_id,
            role=MessageRole.USER,
            content="Hello",
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.tool_calls is None
        assert msg.tool_result is None

    def test_assistant_message_with_tool_calls(self):
        conv_id = uuid4()
        msg = Message(
            conversation_id=conv_id,
            role=MessageRole.ASSISTANT,
            content="Let me check that.",
            tool_calls=[
                ToolCall(
                    id="tc_001",
                    agent_name="weather-agent",
                    input_data={"city": "London"},
                )
            ],
        )
        assert msg.role == MessageRole.ASSISTANT
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].agent_name == "weather-agent"

    def test_tool_result_message(self):
        conv_id = uuid4()
        msg = Message(
            conversation_id=conv_id,
            role=MessageRole.TOOL_RESULT,
            content='{"temperature": 15}',
            tool_result=ToolResult(
                tool_call_id="tc_001",
                agent_name="weather-agent",
                output_data={"temperature": 15},
            ),
        )
        assert msg.role == MessageRole.TOOL_RESULT
        assert msg.tool_result.output_data == {"temperature": 15}
        assert msg.tool_result.error is None

    def test_tool_result_with_error(self):
        result = ToolResult(
            tool_call_id="tc_002",
            agent_name="failing-agent",
            error="connection timeout",
        )
        assert result.output_data is None
        assert result.error == "connection timeout"


class TestAgentIsOrchestrator:
    def test_default_is_false(self):
        from cairn.models.agent import AgentDefinition
        from cairn.models.runtime import RuntimeConfig, RuntimeType
        from cairn.models.trigger import ManualTrigger

        agent = AgentDefinition(
            name="test",
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            trigger=ManualTrigger(),
            runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
        )
        assert agent.is_orchestrator is False

    def test_orchestrator_flag(self):
        from cairn.models.agent import AgentDefinition
        from cairn.models.runtime import RuntimeConfig, RuntimeType
        from cairn.models.trigger import ManualTrigger

        agent = AgentDefinition(
            name="orchestrator",
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            system_prompt="You are a helpful orchestrator.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            trigger=ManualTrigger(),
            runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
            is_orchestrator=True,
        )
        assert agent.is_orchestrator is True
