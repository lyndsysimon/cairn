"""Anthropic LLM client using the official SDK."""

import json
import logging

import anthropic

from cairn.llm.base import ChatMessage, LLMResponse, LLMToolCall, ToolDefinition

logger = logging.getLogger(__name__)


class AnthropicClient:
    """LLM client backed by the Anthropic Messages API."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = anthropic.AsyncAnthropic(**kwargs)

    async def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        api_messages = _build_messages(messages)
        api_tools = _build_tools(tools) if tools else []

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": api_messages,
        }
        if system:
            kwargs["system"] = system
        if api_tools:
            kwargs["tools"] = api_tools

        response = await self._client.messages.create(**kwargs)
        return _parse_response(response)


def _build_messages(messages: list[ChatMessage]) -> list[dict]:
    """Convert internal ChatMessage list to Anthropic API format."""
    result = []
    for msg in messages:
        result.append({"role": msg.role, "content": msg.content})
    return result


def _build_tools(tools: list[ToolDefinition]) -> list[dict]:
    """Convert tool definitions to Anthropic API tool format."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in tools
    ]


def _parse_response(response: anthropic.types.Message) -> LLMResponse:
    """Parse an Anthropic API response into our LLMResponse."""
    text_parts = []
    tool_calls = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            input_data = block.input
            if isinstance(input_data, str):
                input_data = json.loads(input_data)
            tool_calls.append(
                LLMToolCall(
                    id=block.id,
                    name=block.name,
                    input_data=input_data,
                )
            )

    return LLMResponse(
        text="\n".join(text_parts),
        tool_calls=tool_calls,
        stop_reason=response.stop_reason or "",
    )
