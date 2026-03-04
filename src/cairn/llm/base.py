"""LLM client abstraction.

Provides a protocol for language model providers so the orchestration
service stays decoupled from any specific SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolDefinition:
    """Describes a tool the LLM can invoke (maps to a sub-agent)."""

    name: str
    description: str
    input_schema: dict


@dataclass
class LLMToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    input_data: dict


@dataclass
class LLMResponse:
    """The model's response, which may contain text and/or tool calls."""

    text: str = ""
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    stop_reason: str = ""

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class ChatMessage:
    """A single message in the conversation sent to the LLM."""

    role: str  # "user" | "assistant"
    content: str | list[dict]


class LLMClient(Protocol):
    """Interface for LLM providers."""

    async def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a completion request and return the response."""
        ...
