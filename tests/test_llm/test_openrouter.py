"""Tests for the OpenRouter LLM client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cairn.llm.base import ChatMessage, ToolDefinition
from cairn.llm.openrouter import (
    OpenRouterClient,
    _build_messages,
    _build_tools,
    _parse_response,
)


class TestBuildMessages:
    def test_simple_string_user_message(self):
        messages = [ChatMessage(role="user", content="Hello")]
        result = _build_messages("", messages)
        assert result == [{"role": "user", "content": "Hello"}]

    def test_system_prompt_prepended(self):
        messages = [ChatMessage(role="user", content="Hello")]
        result = _build_messages("You are helpful.", messages)
        assert result[0] == {"role": "system", "content": "You are helpful."}
        assert result[1] == {"role": "user", "content": "Hello"}

    def test_empty_system_prompt_not_prepended(self):
        messages = [ChatMessage(role="user", content="Hi")]
        result = _build_messages("", messages)
        assert result[0]["role"] == "user"

    def test_assistant_with_tool_use(self):
        content = [
            {"type": "text", "text": "Let me check"},
            {"type": "tool_use", "id": "call_123", "name": "my-agent", "input": {"x": 1}},
        ]
        messages = [ChatMessage(role="assistant", content=content)]
        result = _build_messages("", messages)
        assert len(result) == 1
        msg = result[0]
        assert msg["role"] == "assistant"
        assert msg["content"] == "Let me check"
        assert len(msg["tool_calls"]) == 1
        tc = msg["tool_calls"][0]
        assert tc["id"] == "call_123"
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "my-agent"
        assert '"x": 1' in tc["function"]["arguments"]

    def test_assistant_tool_use_no_text(self):
        content = [
            {"type": "tool_use", "id": "call_abc", "name": "agent", "input": {}},
        ]
        messages = [ChatMessage(role="assistant", content=content)]
        result = _build_messages("", messages)
        assert result[0]["content"] is None
        assert len(result[0]["tool_calls"]) == 1

    def test_user_with_tool_result(self):
        content = [
            {"type": "tool_result", "tool_use_id": "call_123", "content": '{"ok": true}'},
        ]
        messages = [ChatMessage(role="user", content=content)]
        result = _build_messages("", messages)
        assert len(result) == 1
        assert result[0]["role"] == "tool"
        assert result[0]["tool_call_id"] == "call_123"
        assert result[0]["content"] == '{"ok": true}'

    def test_multiple_tool_results_expanded(self):
        content = [
            {"type": "tool_result", "tool_use_id": "call_1", "content": "a"},
            {"type": "tool_result", "tool_use_id": "call_2", "content": "b"},
        ]
        messages = [ChatMessage(role="user", content=content)]
        result = _build_messages("", messages)
        assert len(result) == 2
        assert result[0]["tool_call_id"] == "call_1"
        assert result[1]["tool_call_id"] == "call_2"

    def test_simple_assistant_text_message(self):
        messages = [ChatMessage(role="assistant", content="Done.")]
        result = _build_messages("", messages)
        assert result == [{"role": "assistant", "content": "Done."}]


class TestBuildTools:
    def test_single_tool(self):
        tools = [
            ToolDefinition(
                name="my-agent",
                description="Does stuff",
                input_schema={"type": "object", "properties": {}},
            )
        ]
        result = _build_tools(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "my-agent"
        assert result[0]["function"]["description"] == "Does stuff"
        assert result[0]["function"]["parameters"] == {"type": "object", "properties": {}}

    def test_multiple_tools(self):
        tools = [
            ToolDefinition(name="a", description="A", input_schema={}),
            ToolDefinition(name="b", description="B", input_schema={}),
        ]
        result = _build_tools(tools)
        assert len(result) == 2
        assert result[0]["function"]["name"] == "a"
        assert result[1]["function"]["name"] == "b"


class TestParseResponse:
    def _make_response(self, content, tool_calls=None, finish_reason="stop"):
        response = MagicMock()
        choice = MagicMock()
        choice.message.content = content
        choice.message.tool_calls = tool_calls
        choice.finish_reason = finish_reason
        response.choices = [choice]
        return response

    def test_text_response(self):
        response = self._make_response("Hello there")
        result = _parse_response(response)
        assert result.text == "Hello there"
        assert not result.has_tool_calls
        assert result.stop_reason == "stop"

    def test_none_content_becomes_empty_string(self):
        response = self._make_response(None)
        result = _parse_response(response)
        assert result.text == ""

    def test_tool_call_response(self):
        tc = MagicMock()
        tc.id = "call_abc"
        tc.function.name = "my-agent"
        tc.function.arguments = '{"x": 1}'
        response = self._make_response(None, tool_calls=[tc], finish_reason="tool_calls")

        result = _parse_response(response)
        assert result.has_tool_calls
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "call_abc"
        assert result.tool_calls[0].name == "my-agent"
        assert result.tool_calls[0].input_data == {"x": 1}
        assert result.stop_reason == "tool_calls"

    def test_multiple_tool_calls(self):
        tc1 = MagicMock()
        tc1.id = "call_1"
        tc1.function.name = "agent-a"
        tc1.function.arguments = '{"a": 1}'
        tc2 = MagicMock()
        tc2.id = "call_2"
        tc2.function.name = "agent-b"
        tc2.function.arguments = '{"b": 2}'
        response = self._make_response(None, tool_calls=[tc1, tc2])

        result = _parse_response(response)
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].name == "agent-a"
        assert result.tool_calls[1].name == "agent-b"


class TestOpenRouterClientComplete:
    @pytest.mark.asyncio
    async def test_complete_text_response(self):
        choice = MagicMock()
        choice.message.content = "Hello from OpenRouter"
        choice.message.tool_calls = None
        choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [choice]

        with patch("cairn.llm.openrouter.openai") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.AsyncOpenAI.return_value = mock_client

            client = OpenRouterClient(api_key="test-key")
            result = await client.complete(
                model="openai/gpt-4",
                system="You are helpful.",
                messages=[ChatMessage(role="user", content="Hi")],
            )

        assert result.text == "Hello from OpenRouter"
        assert not result.has_tool_calls
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4"
        assert call_kwargs["max_tokens"] == 4096
        # System prompt should appear as first message
        msgs = call_kwargs["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You are helpful."

    @pytest.mark.asyncio
    async def test_complete_with_tools(self):
        choice = MagicMock()
        choice.message.content = None
        tc = MagicMock()
        tc.id = "call_xyz"
        tc.function.name = "my-agent"
        tc.function.arguments = "{}"
        choice.message.tool_calls = [tc]
        choice.finish_reason = "tool_calls"
        mock_response = MagicMock()
        mock_response.choices = [choice]

        with patch("cairn.llm.openrouter.openai") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.AsyncOpenAI.return_value = mock_client

            client = OpenRouterClient(api_key="test-key")
            tools = [ToolDefinition(name="my-agent", description="desc", input_schema={})]
            result = await client.complete(
                model="openai/gpt-4",
                system="",
                messages=[ChatMessage(role="user", content="Go")],
                tools=tools,
            )

        assert result.has_tool_calls
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"][0]["function"]["name"] == "my-agent"

    @pytest.mark.asyncio
    async def test_complete_uses_default_base_url(self):
        with patch("cairn.llm.openrouter.openai") as mock_openai:
            mock_openai.AsyncOpenAI.return_value = MagicMock()
            OpenRouterClient(api_key="key")
            call_kwargs = mock_openai.AsyncOpenAI.call_args[1]
            assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"

    @pytest.mark.asyncio
    async def test_complete_uses_custom_base_url(self):
        with patch("cairn.llm.openrouter.openai") as mock_openai:
            mock_openai.AsyncOpenAI.return_value = MagicMock()
            OpenRouterClient(api_key="key", base_url="https://custom.example.com/v1")
            call_kwargs = mock_openai.AsyncOpenAI.call_args[1]
            assert call_kwargs["base_url"] == "https://custom.example.com/v1"


class TestListModels:
    @pytest.mark.asyncio
    async def test_list_models_with_names(self):
        model1 = MagicMock()
        model1.id = "openai/gpt-4"
        model1.name = "GPT-4"
        model2 = MagicMock()
        model2.id = "anthropic/claude-3"
        model2.name = "Claude 3"

        mock_page = MagicMock()
        mock_page.data = [model1, model2]

        with patch("cairn.llm.openrouter.openai") as mock_openai:
            mock_client = MagicMock()
            mock_client.models.list = AsyncMock(return_value=mock_page)
            mock_openai.AsyncOpenAI.return_value = mock_client

            models = await OpenRouterClient.list_models(api_key="test-key")

        assert len(models) == 2
        assert models[0].model_id == "openai/gpt-4"
        assert models[0].display_name == "GPT-4"
        assert models[1].model_id == "anthropic/claude-3"
        assert models[1].display_name == "Claude 3"

    @pytest.mark.asyncio
    async def test_list_models_falls_back_to_id_when_no_name(self):
        model = MagicMock()
        model.id = "some/model"
        model.name = None  # No display name

        mock_page = MagicMock()
        mock_page.data = [model]

        with patch("cairn.llm.openrouter.openai") as mock_openai:
            mock_client = MagicMock()
            mock_client.models.list = AsyncMock(return_value=mock_page)
            mock_openai.AsyncOpenAI.return_value = mock_client

            models = await OpenRouterClient.list_models(api_key="test-key")

        assert models[0].display_name == "some/model"

    @pytest.mark.asyncio
    async def test_list_models_uses_custom_base_url(self):
        mock_page = MagicMock()
        mock_page.data = []

        with patch("cairn.llm.openrouter.openai") as mock_openai:
            mock_client = MagicMock()
            mock_client.models.list = AsyncMock(return_value=mock_page)
            mock_openai.AsyncOpenAI.return_value = mock_client

            await OpenRouterClient.list_models(
                api_key="key", base_url="https://custom.example.com/v1"
            )

        call_kwargs = mock_openai.AsyncOpenAI.call_args[1]
        assert call_kwargs["base_url"] == "https://custom.example.com/v1"
