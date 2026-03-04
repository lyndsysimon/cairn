"""Tests for the Anthropic LLM client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cairn.llm.anthropic import AnthropicClient, _parse_response
from cairn.llm.base import ChatMessage


class TestParseResponse:
    def test_text_response(self):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Hello, I can help with that."
        response.content = [text_block]
        response.stop_reason = "end_turn"

        result = _parse_response(response)
        assert result.text == "Hello, I can help with that."
        assert not result.has_tool_calls
        assert result.stop_reason == "end_turn"

    def test_tool_use_response(self):
        response = MagicMock()
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "toolu_abc"
        tool_block.name = "weather-agent"
        tool_block.input = {"city": "London"}
        response.content = [tool_block]
        response.stop_reason = "tool_use"

        result = _parse_response(response)
        assert result.has_tool_calls
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "toolu_abc"
        assert result.tool_calls[0].name == "weather-agent"
        assert result.tool_calls[0].input_data == {"city": "London"}

    def test_mixed_text_and_tool_use(self):
        response = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Let me check the weather."
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "toolu_def"
        tool_block.name = "weather-agent"
        tool_block.input = {"city": "Paris"}
        response.content = [text_block, tool_block]
        response.stop_reason = "tool_use"

        result = _parse_response(response)
        assert result.text == "Let me check the weather."
        assert result.has_tool_calls
        assert result.tool_calls[0].name == "weather-agent"

    def test_multiple_tool_calls(self):
        response = MagicMock()
        tool1 = MagicMock()
        tool1.type = "tool_use"
        tool1.id = "toolu_1"
        tool1.name = "agent-a"
        tool1.input = {"x": 1}
        tool2 = MagicMock()
        tool2.type = "tool_use"
        tool2.id = "toolu_2"
        tool2.name = "agent-b"
        tool2.input = {"y": 2}
        response.content = [tool1, tool2]
        response.stop_reason = "tool_use"

        result = _parse_response(response)
        assert len(result.tool_calls) == 2


class TestAnthropicClientComplete:
    @pytest.mark.asyncio
    async def test_complete_calls_api(self):
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Response from Claude"
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_response.stop_reason = "end_turn"

        with patch("cairn.llm.anthropic.anthropic") as mock_anthropic:
            mock_async_client = MagicMock()
            mock_async_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.AsyncAnthropic.return_value = mock_async_client

            client = AnthropicClient(api_key="test-key")
            result = await client.complete(
                model="claude-sonnet-4-20250514",
                system="You are helpful.",
                messages=[ChatMessage(role="user", content="Hi")],
            )

        assert result.text == "Response from Claude"
        mock_async_client.messages.create.assert_called_once()
        call_kwargs = mock_async_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_kwargs["system"] == "You are helpful."
