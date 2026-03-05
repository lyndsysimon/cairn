"""OpenRouter LLM client using the OpenAI-compatible API."""

from __future__ import annotations

import json
import logging

import openai

from cairn.llm.base import ChatMessage, LLMResponse, LLMToolCall, ToolDefinition
from cairn.models.provider import ModelConfig

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient:
    """LLM client backed by the OpenRouter API (OpenAI-compatible)."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or _DEFAULT_BASE_URL,
        )

    async def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        api_messages = _build_messages(system, messages)
        api_tools = _build_tools(tools) if tools else []

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": api_messages,
        }
        if api_tools:
            kwargs["tools"] = api_tools

        response = await self._client.chat.completions.create(**kwargs)
        return _parse_response(response)

    @classmethod
    async def list_models(cls, api_key: str, base_url: str | None = None) -> list[ModelConfig]:
        """Fetch available models from the provider API."""
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or _DEFAULT_BASE_URL,
        )
        page = await client.models.list()
        result = []
        for model in page.data:
            name = getattr(model, "name", None)
            display_name = name if isinstance(name, str) and name else model.id
            result.append(ModelConfig(model_id=model.id, display_name=display_name))
        return result


def _build_messages(system: str, messages: list[ChatMessage]) -> list[dict]:
    """Convert system prompt and internal ChatMessages to OpenAI chat format."""
    result: list[dict] = []
    if system:
        result.append({"role": "system", "content": system})
    for msg in messages:
        if isinstance(msg.content, str):
            result.append({"role": msg.role, "content": msg.content})
        elif msg.role == "assistant":
            # Reconstruct assistant message with optional tool_calls
            text_parts = []
            tool_calls = []
            for block in msg.content:
                if block["type"] == "text":
                    text_parts.append(block["text"])
                elif block["type"] == "tool_use":
                    tool_calls.append(
                        {
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block["input"]),
                            },
                        }
                    )
            entry: dict = {"role": "assistant"}
            entry["content"] = "\n".join(text_parts) if text_parts else None
            if tool_calls:
                entry["tool_calls"] = tool_calls
            result.append(entry)
        elif msg.role == "user":
            # User messages with list content contain tool_result blocks.
            # Each becomes a separate "tool" role message in OpenAI format.
            for block in msg.content:
                if block["type"] == "tool_result":
                    result.append(
                        {
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": block["content"],
                        }
                    )
                elif block["type"] == "text":
                    result.append({"role": "user", "content": block["text"]})
    return result


def _build_tools(tools: list[ToolDefinition]) -> list[dict]:
    """Convert tool definitions to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
    ]


def _parse_response(response) -> LLMResponse:
    """Parse an OpenAI-compatible chat completion response into LLMResponse."""
    choice = response.choices[0]
    message = choice.message

    text = message.content or ""
    tool_calls = []

    if message.tool_calls:
        for tc in message.tool_calls:
            input_data = json.loads(tc.function.arguments)
            tool_calls.append(
                LLMToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input_data=input_data,
                )
            )

    return LLMResponse(
        text=text,
        tool_calls=tool_calls,
        stop_reason=choice.finish_reason or "",
    )
