"""Tests for the orchestration service — the core agentic loop."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from cairn.llm.base import LLMResponse, LLMToolCall, ToolDefinition
from cairn.models.agent import AgentDefinition
from cairn.models.conversation import Conversation, Message, MessageRole
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.trigger import ManualTrigger
from cairn.orchestration.service import OrchestrationService, _messages_to_chat


def _make_orchestrator() -> AgentDefinition:
    return AgentDefinition(
        name="orchestrator",
        description="The main orchestrator",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        system_prompt="You are a helpful assistant that delegates tasks.",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger=ManualTrigger(),
        runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
        is_orchestrator=True,
    )


def _make_security():
    pipeline = AsyncMock()
    pipeline.inspect_outbound = AsyncMock(side_effect=lambda prompt, _: prompt)
    pipeline.inspect_inbound = AsyncMock(side_effect=lambda content: (content, []))
    pipeline.for_agent = lambda _agent: pipeline
    return pipeline


def _make_conn():
    conn = AsyncMock()
    conn.commit = AsyncMock()
    return conn


class TestCreateConversation:
    @pytest.mark.asyncio
    async def test_create_conversation(self):
        orchestrator = _make_orchestrator()

        async def llm_factory(provider, conn):
            return AsyncMock()

        tool_registry = AsyncMock()
        security = _make_security()
        conn = _make_conn()

        service = OrchestrationService(
            llm_client_factory=llm_factory,
            tool_registry=tool_registry,
            security=security,
        )

        with (
            patch("cairn.orchestration.service.agent_repo") as mock_agent_repo,
            patch("cairn.orchestration.service.conversation_repo") as mock_conv_repo,
        ):
            mock_agent_repo.get_by_id = AsyncMock(return_value=orchestrator)
            mock_conv_repo.create = AsyncMock(
                side_effect=lambda conn, conv: conv,
            )

            conversation = await service.create_conversation(
                conn, orchestrator.id, title="Test chat"
            )

        assert conversation.orchestrator_agent_id == orchestrator.id
        assert conversation.title == "Test chat"

    @pytest.mark.asyncio
    async def test_create_conversation_rejects_non_orchestrator(self):
        agent = AgentDefinition(
            name="regular-agent",
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            trigger=ManualTrigger(),
            runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
            is_orchestrator=False,
        )

        async def llm_factory(provider, conn):
            return AsyncMock()

        service = OrchestrationService(
            llm_client_factory=llm_factory,
            tool_registry=AsyncMock(),
            security=_make_security(),
        )
        conn = _make_conn()

        with patch("cairn.orchestration.service.agent_repo") as mock_agent_repo:
            mock_agent_repo.get_by_id = AsyncMock(return_value=agent)
            with pytest.raises(ValueError, match="not an orchestrator"):
                await service.create_conversation(conn, agent.id)

    @pytest.mark.asyncio
    async def test_create_conversation_rejects_missing_agent(self):
        async def llm_factory(provider, conn):
            return AsyncMock()

        service = OrchestrationService(
            llm_client_factory=llm_factory,
            tool_registry=AsyncMock(),
            security=_make_security(),
        )
        conn = _make_conn()

        with patch("cairn.orchestration.service.agent_repo") as mock_agent_repo:
            mock_agent_repo.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(ValueError, match="not found"):
                await service.create_conversation(conn, uuid4())


class TestSendMessageSimple:
    """Test the send_message flow with a direct text response (no tool calls)."""

    @pytest.mark.asyncio
    async def test_simple_text_response(self):
        orchestrator = _make_orchestrator()
        conv_id = uuid4()
        conversation = Conversation(
            id=conv_id,
            orchestrator_agent_id=orchestrator.id,
        )

        # Mock LLM that returns a simple text response
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            return_value=LLMResponse(text="Hello! How can I help?", stop_reason="end_turn")
        )

        async def llm_factory(provider, conn):
            return mock_llm

        tool_registry = AsyncMock()
        tool_registry.get_tool_definitions = AsyncMock(return_value=([], {}))
        security = _make_security()
        conn = _make_conn()

        service = OrchestrationService(
            llm_client_factory=llm_factory,
            tool_registry=tool_registry,
            security=security,
        )

        saved_messages = []

        with (
            patch("cairn.orchestration.service.conversation_repo") as mock_conv_repo,
            patch("cairn.orchestration.service.agent_repo") as mock_agent_repo,
            patch("cairn.orchestration.service.message_repo") as mock_msg_repo,
        ):
            mock_conv_repo.get_by_id = AsyncMock(return_value=conversation)
            mock_conv_repo.touch = AsyncMock()
            mock_agent_repo.get_by_id = AsyncMock(return_value=orchestrator)
            mock_msg_repo.list_by_conversation = AsyncMock(return_value=[])

            def capture_create(conn, msg):
                saved_messages.append(msg)
                return msg

            mock_msg_repo.create = AsyncMock(side_effect=capture_create)

            result = await service.send_message(conn, conv_id, "Hi there")

        # Should have saved user message + assistant message
        assert len(saved_messages) == 2
        assert saved_messages[0].role == MessageRole.USER
        assert saved_messages[0].content == "Hi there"
        assert saved_messages[1].role == MessageRole.ASSISTANT
        assert saved_messages[1].content == "Hello! How can I help?"

        # Return value should be the assistant message
        assert result.role == MessageRole.ASSISTANT
        assert result.content == "Hello! How can I help?"


class TestSendMessageWithToolCalls:
    """Test the agentic loop with tool calls."""

    @pytest.mark.asyncio
    async def test_single_tool_call_then_text(self):
        orchestrator = _make_orchestrator()
        conv_id = uuid4()
        conversation = Conversation(
            id=conv_id,
            orchestrator_agent_id=orchestrator.id,
        )

        sub_agent = AgentDefinition(
            name="weather",
            description="Get weather info",
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
            output_schema={"type": "object"},
            trigger=ManualTrigger(),
            runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
        )

        # LLM response sequence: first tool_use, then text
        tool_response = LLMResponse(
            text="Let me check the weather.",
            tool_calls=[
                LLMToolCall(id="tc_1", name="weather", input_data={"city": "London"}),
            ],
            stop_reason="tool_use",
        )
        final_response = LLMResponse(
            text="The weather in London is 15C and cloudy.",
            stop_reason="end_turn",
        )
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(side_effect=[tool_response, final_response])

        async def llm_factory(provider, conn):
            return mock_llm

        # Tool registry returns weather agent as a tool
        tool_def = ToolDefinition(
            name="weather",
            description="Get weather info",
            input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
        )
        tool_registry = AsyncMock()
        tool_registry.get_tool_definitions = AsyncMock(
            return_value=([tool_def], {"weather": sub_agent})
        )
        tool_registry.execute_tool_call = AsyncMock(
            return_value={"temperature": 15, "condition": "cloudy"}
        )

        security = _make_security()
        conn = _make_conn()

        service = OrchestrationService(
            llm_client_factory=llm_factory,
            tool_registry=tool_registry,
            security=security,
        )

        saved_messages = []

        with (
            patch("cairn.orchestration.service.conversation_repo") as mock_conv_repo,
            patch("cairn.orchestration.service.agent_repo") as mock_agent_repo,
            patch("cairn.orchestration.service.message_repo") as mock_msg_repo,
        ):
            mock_conv_repo.get_by_id = AsyncMock(return_value=conversation)
            mock_conv_repo.touch = AsyncMock()
            mock_agent_repo.get_by_id = AsyncMock(return_value=orchestrator)
            mock_msg_repo.list_by_conversation = AsyncMock(return_value=[])

            def capture_create(conn, msg):
                saved_messages.append(msg)
                return msg

            mock_msg_repo.create = AsyncMock(side_effect=capture_create)

            await service.send_message(conn, conv_id, "What's the weather in London?")

        # Messages: user, assistant (tool_use), tool_result, assistant (final)
        assert len(saved_messages) == 4
        assert saved_messages[0].role == MessageRole.USER
        assert saved_messages[1].role == MessageRole.ASSISTANT
        assert saved_messages[1].tool_calls is not None
        assert len(saved_messages[1].tool_calls) == 1
        assert saved_messages[2].role == MessageRole.TOOL_RESULT
        assert saved_messages[3].role == MessageRole.ASSISTANT
        assert saved_messages[3].content == "The weather in London is 15C and cloudy."

        # Tool registry should have been called
        tool_registry.execute_tool_call.assert_called_once()

        # LLM should have been called twice
        assert mock_llm.complete.call_count == 2


class TestSendMessageSecurity:
    """Test that security middleware is applied."""

    @pytest.mark.asyncio
    async def test_outbound_inspection_on_user_input(self):
        orchestrator = _make_orchestrator()
        conv_id = uuid4()
        conversation = Conversation(id=conv_id, orchestrator_agent_id=orchestrator.id)

        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(return_value=LLMResponse(text="OK", stop_reason="end_turn"))

        async def llm_factory(provider, conn):
            return mock_llm

        # Security that redacts "secret123"
        security = AsyncMock()
        security.inspect_outbound = AsyncMock(
            side_effect=lambda text, _: text.replace("secret123", "[REDACTED]")
        )
        security.inspect_inbound = AsyncMock(side_effect=lambda content: (content, []))
        security.for_agent = lambda _agent: security

        tool_registry = AsyncMock()
        tool_registry.get_tool_definitions = AsyncMock(return_value=([], {}))

        conn = _make_conn()
        service = OrchestrationService(
            llm_client_factory=llm_factory,
            tool_registry=tool_registry,
            security=security,
        )

        saved_messages = []

        with (
            patch("cairn.orchestration.service.conversation_repo") as mock_conv_repo,
            patch("cairn.orchestration.service.agent_repo") as mock_agent_repo,
            patch("cairn.orchestration.service.message_repo") as mock_msg_repo,
        ):
            mock_conv_repo.get_by_id = AsyncMock(return_value=conversation)
            mock_conv_repo.touch = AsyncMock()
            mock_agent_repo.get_by_id = AsyncMock(return_value=orchestrator)
            mock_msg_repo.list_by_conversation = AsyncMock(return_value=[])
            mock_msg_repo.create = AsyncMock(
                side_effect=lambda conn, msg: (saved_messages.append(msg), msg)[1]
            )

            await service.send_message(conn, conv_id, "My password is secret123")

        # The user message should have been sanitized
        assert saved_messages[0].content == "My password is [REDACTED]"


class TestMaxToolRounds:
    """Test that the agentic loop respects the max rounds limit."""

    @pytest.mark.asyncio
    async def test_max_rounds_produces_fallback(self):
        orchestrator = _make_orchestrator()
        conv_id = uuid4()
        conversation = Conversation(id=conv_id, orchestrator_agent_id=orchestrator.id)

        # LLM always returns tool calls (never stops)
        infinite_tool_response = LLMResponse(
            text="",
            tool_calls=[
                LLMToolCall(id="tc_loop", name="agent-a", input_data={}),
            ],
            stop_reason="tool_use",
        )
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(return_value=infinite_tool_response)

        async def llm_factory(provider, conn):
            return mock_llm

        sub_agent = AgentDefinition(
            name="agent-a",
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            trigger=ManualTrigger(),
            runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
        )
        tool_def = ToolDefinition(name="agent-a", description="Agent A", input_schema={})
        tool_registry = AsyncMock()
        tool_registry.get_tool_definitions = AsyncMock(
            return_value=([tool_def], {"agent-a": sub_agent})
        )
        tool_registry.execute_tool_call = AsyncMock(return_value={"status": "ok"})

        security = _make_security()
        conn = _make_conn()

        service = OrchestrationService(
            llm_client_factory=llm_factory,
            tool_registry=tool_registry,
            security=security,
        )

        with (
            patch("cairn.orchestration.service.conversation_repo") as mock_conv_repo,
            patch("cairn.orchestration.service.agent_repo") as mock_agent_repo,
            patch("cairn.orchestration.service.message_repo") as mock_msg_repo,
            patch("cairn.orchestration.service._MAX_TOOL_ROUNDS", 3),
        ):
            mock_conv_repo.get_by_id = AsyncMock(return_value=conversation)
            mock_conv_repo.touch = AsyncMock()
            mock_agent_repo.get_by_id = AsyncMock(return_value=orchestrator)
            mock_msg_repo.list_by_conversation = AsyncMock(return_value=[])
            mock_msg_repo.create = AsyncMock(side_effect=lambda conn, msg: msg)

            result = await service.send_message(conn, conv_id, "Do something infinite")

        # Should have hit the max rounds and returned a fallback message
        assert result.role == MessageRole.ASSISTANT
        assert "maximum number of steps" in result.content

        # LLM should have been called exactly 3 times (max rounds)
        assert mock_llm.complete.call_count == 3


class TestMessagesToChat:
    def test_empty_history(self):
        assert _messages_to_chat([]) == []

    def test_user_and_assistant(self):
        conv_id = uuid4()
        messages = [
            Message(conversation_id=conv_id, role=MessageRole.USER, content="Hello"),
            Message(conversation_id=conv_id, role=MessageRole.ASSISTANT, content="Hi!"),
        ]
        chat = _messages_to_chat(messages)
        assert len(chat) == 2
        assert chat[0].role == "user"
        assert chat[0].content == "Hello"
        assert chat[1].role == "assistant"
        assert chat[1].content == "Hi!"

    def test_tool_call_and_result_reconstruction(self):
        from cairn.models.conversation import ToolCall, ToolResult

        conv_id = uuid4()
        messages = [
            Message(conversation_id=conv_id, role=MessageRole.USER, content="Check weather"),
            Message(
                conversation_id=conv_id,
                role=MessageRole.ASSISTANT,
                content="",
                tool_calls=[ToolCall(id="tc_1", agent_name="weather", input_data={"city": "NYC"})],
            ),
            Message(
                conversation_id=conv_id,
                role=MessageRole.TOOL_RESULT,
                content='{"temp": 20}',
                tool_result=ToolResult(
                    tool_call_id="tc_1",
                    agent_name="weather",
                    output_data={"temp": 20},
                ),
            ),
            Message(
                conversation_id=conv_id,
                role=MessageRole.ASSISTANT,
                content="It's 20C in NYC.",
            ),
        ]
        chat = _messages_to_chat(messages)
        assert len(chat) == 4
        # First: user text
        assert chat[0].role == "user"
        # Second: assistant with tool_use blocks
        assert chat[1].role == "assistant"
        assert isinstance(chat[1].content, list)
        assert chat[1].content[0]["type"] == "tool_use"
        # Third: user message with tool_result
        assert chat[2].role == "user"
        assert isinstance(chat[2].content, list)
        assert chat[2].content[0]["type"] == "tool_result"
        # Fourth: assistant text
        assert chat[3].role == "assistant"
        assert chat[3].content == "It's 20C in NYC."

    def test_consecutive_tool_results_grouped(self):
        from cairn.models.conversation import ToolCall, ToolResult

        conv_id = uuid4()
        messages = [
            Message(conversation_id=conv_id, role=MessageRole.USER, content="Do both"),
            Message(
                conversation_id=conv_id,
                role=MessageRole.ASSISTANT,
                content="",
                tool_calls=[
                    ToolCall(id="tc_1", agent_name="a", input_data={}),
                    ToolCall(id="tc_2", agent_name="b", input_data={}),
                ],
            ),
            Message(
                conversation_id=conv_id,
                role=MessageRole.TOOL_RESULT,
                content='{"x": 1}',
                tool_result=ToolResult(tool_call_id="tc_1", agent_name="a", output_data={"x": 1}),
            ),
            Message(
                conversation_id=conv_id,
                role=MessageRole.TOOL_RESULT,
                content='{"y": 2}',
                tool_result=ToolResult(tool_call_id="tc_2", agent_name="b", output_data={"y": 2}),
            ),
        ]
        chat = _messages_to_chat(messages)
        # User, assistant (tool_use), user (both tool_results grouped)
        assert len(chat) == 3
        assert chat[2].role == "user"
        assert isinstance(chat[2].content, list)
        assert len(chat[2].content) == 2
        assert chat[2].content[0]["tool_use_id"] == "tc_1"
        assert chat[2].content[1]["tool_use_id"] == "tc_2"
