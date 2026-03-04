"""Tests for the LLM client base types."""

from cairn.llm.base import ChatMessage, LLMResponse, LLMToolCall, ToolDefinition


class TestToolDefinition:
    def test_creation(self):
        tool = ToolDefinition(
            name="search-agent",
            description="Search the web",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )
        assert tool.name == "search-agent"
        assert tool.description == "Search the web"


class TestLLMResponse:
    def test_text_only_response(self):
        resp = LLMResponse(text="Hello!", stop_reason="end_turn")
        assert resp.text == "Hello!"
        assert not resp.has_tool_calls
        assert resp.tool_calls == []

    def test_tool_call_response(self):
        resp = LLMResponse(
            text="",
            tool_calls=[
                LLMToolCall(id="tc_1", name="search", input_data={"q": "test"}),
            ],
            stop_reason="tool_use",
        )
        assert resp.has_tool_calls
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "search"

    def test_mixed_response(self):
        resp = LLMResponse(
            text="Let me search that.",
            tool_calls=[
                LLMToolCall(id="tc_1", name="search", input_data={"q": "test"}),
            ],
        )
        assert resp.has_tool_calls
        assert resp.text == "Let me search that."


class TestChatMessage:
    def test_text_content(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_structured_content(self):
        msg = ChatMessage(
            role="user",
            content=[
                {"type": "tool_result", "tool_use_id": "tc_1", "content": "{}"},
            ],
        )
        assert isinstance(msg.content, list)
