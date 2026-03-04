"""Orchestration service — the core agentic conversation loop.

Manages multi-turn conversations between the user and the orchestration
agent.  When the LLM invokes tools (sub-agents), this service executes
them via the AgentToolRegistry and feeds the results back until the LLM
produces a final text response.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any
from uuid import UUID

from psycopg import AsyncConnection

from cairn.db.repositories import agent_repo, conversation_repo, message_repo

if TYPE_CHECKING:
    from cairn.credentials.base import CredentialStore
from cairn.llm.base import ChatMessage, LLMClient, LLMResponse, ToolDefinition
from cairn.models.agent import AgentDefinition
from cairn.models.conversation import (
    Conversation,
    Message,
    MessageRole,
    ToolCall,
    ToolResult,
)
from cairn.orchestration.tools import AgentToolRegistry
from cairn.security.base import SecurityPipeline

logger = logging.getLogger(__name__)

# Maximum number of LLM round-trips (tool call loops) per user message.
_MAX_TOOL_ROUNDS = 20

# Type alias for the factory function that creates LLM clients.
# Takes (provider_name, conn) and returns an LLMClient.
LLMClientFactory = Callable[[str, AsyncConnection], Coroutine[Any, Any, LLMClient]]


class OrchestrationService:
    """Drives multi-turn conversations for an orchestration agent."""

    def __init__(
        self,
        llm_client_factory: LLMClientFactory,
        tool_registry: AgentToolRegistry,
        security: SecurityPipeline,
        credential_store: CredentialStore | None = None,
    ) -> None:
        self._llm_client_factory = llm_client_factory
        self._tool_registry = tool_registry
        self._security = security
        self._credential_store = credential_store

    async def create_conversation(
        self,
        conn: AsyncConnection,
        orchestrator_agent_id: UUID,
        title: str = "",
    ) -> Conversation:
        """Start a new conversation with the given orchestrator agent."""
        agent = await agent_repo.get_by_id(conn, orchestrator_agent_id)
        if agent is None:
            raise ValueError(f"Agent {orchestrator_agent_id} not found")
        if not agent.is_orchestrator:
            raise ValueError(f"Agent {agent.name} is not an orchestrator")

        conversation = Conversation(
            orchestrator_agent_id=orchestrator_agent_id,
            title=title,
        )
        conversation = await conversation_repo.create(conn, conversation)
        await conn.commit()
        return conversation

    async def send_message(
        self,
        conn: AsyncConnection,
        conversation_id: UUID,
        user_text: str,
    ) -> Message:
        """Send a user message and drive the LLM to produce a response.

        This method:
        1. Persists the user message
        2. Builds tool definitions from available sub-agents
        3. Enters the agentic loop: call LLM -> execute tools -> repeat
        4. Persists and returns the final assistant message

        Returns the assistant's final Message.
        """
        # Load conversation and orchestrator agent
        conversation = await conversation_repo.get_by_id(conn, conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        agent = await agent_repo.get_by_id(conn, conversation.orchestrator_agent_id)
        if agent is None:
            raise ValueError("Orchestrator agent not found")

        # Build security pipeline for this agent
        pipeline = self._security.for_agent(agent)

        # Resolve credentials for security inspection
        credential_values = await self._resolve_credential_values(agent)

        # Security: inspect user input for leaked credentials
        sanitized_input = await pipeline.inspect_outbound(user_text, credential_values)
        if sanitized_input != user_text:
            logger.warning(
                "Security middleware sanitized user input for conversation %s",
                conversation_id,
            )
            user_text = sanitized_input

        # Persist user message
        user_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=user_text,
        )
        user_msg = await message_repo.create(conn, user_msg)
        await conn.commit()

        # Load full conversation history
        history = await message_repo.list_by_conversation(conn, conversation_id)

        # Build tool definitions from available sub-agents
        tools, agent_map = await self._tool_registry.get_tool_definitions(conn)

        # Get LLM client
        llm_client = await self._get_llm_client(agent, conn)

        # Convert history to LLM chat messages
        chat_messages = _messages_to_chat(history)

        # Agentic loop
        final_message = await self._agentic_loop(
            conn=conn,
            agent=agent,
            conversation_id=conversation_id,
            chat_messages=chat_messages,
            tools=tools,
            agent_map=agent_map,
            llm_client=llm_client,
            pipeline=pipeline,
            credential_values=credential_values,
        )

        # Update conversation timestamp
        await conversation_repo.touch(conn, conversation_id)
        await conn.commit()

        return final_message

    async def _agentic_loop(
        self,
        *,
        conn: AsyncConnection,
        agent: AgentDefinition,
        conversation_id: UUID,
        chat_messages: list[ChatMessage],
        tools: list[ToolDefinition],
        agent_map: dict[str, AgentDefinition],
        llm_client: LLMClient,
        pipeline: SecurityPipeline,
        credential_values: list[str],
    ) -> Message:
        """Call the LLM in a loop until it produces a final text response."""
        for round_num in range(_MAX_TOOL_ROUNDS):
            logger.debug(
                "Orchestration loop round %d for conversation %s",
                round_num,
                conversation_id,
            )

            # Security: inspect the full prompt going to the LLM
            prompt_text = json.dumps(
                [{"role": m.role, "content": str(m.content)} for m in chat_messages]
            )
            await pipeline.inspect_outbound(prompt_text, credential_values)

            # Call the LLM
            response: LLMResponse = await llm_client.complete(
                model=agent.model_name,
                system=agent.system_prompt,
                messages=chat_messages,
                tools=tools if tools else None,
            )

            if not response.has_tool_calls:
                # Final text response — inspect inbound and persist
                content = response.text
                sanitized_content, warnings = await pipeline.inspect_inbound(content)
                if warnings:
                    logger.warning(
                        "Security warnings on orchestrator response (conversation %s): %s",
                        conversation_id,
                        warnings,
                    )

                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=sanitized_content,
                )
                assistant_msg = await message_repo.create(conn, assistant_msg)
                await conn.commit()
                return assistant_msg

            # LLM wants to call tools — persist assistant message with tool calls
            llm_tool_calls = [
                ToolCall(id=tc.id, agent_name=tc.name, input_data=tc.input_data)
                for tc in response.tool_calls
            ]
            assistant_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=response.text,
                tool_calls=llm_tool_calls,
            )
            assistant_msg = await message_repo.create(conn, assistant_msg)
            await conn.commit()

            # Add assistant message to chat history (with tool_use blocks)
            assistant_content: list[dict] = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            for tc in response.tool_calls:
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.input_data,
                    }
                )
            chat_messages.append(ChatMessage(role="assistant", content=assistant_content))

            # Execute each tool call and collect results
            tool_result_blocks: list[dict] = []
            for tc in response.tool_calls:
                result = await self._tool_registry.execute_tool_call(tc, agent_map, conn)

                # Security: inspect inbound tool result
                result_str = json.dumps(result)
                sanitized_result, warnings = await pipeline.inspect_inbound(result_str)
                if warnings:
                    logger.warning("Security warnings on tool result %s: %s", tc.id, warnings)
                    result = json.loads(sanitized_result)

                # Persist tool result message
                tool_result_msg = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.TOOL_RESULT,
                    content=json.dumps(result),
                    tool_result=ToolResult(
                        tool_call_id=tc.id,
                        agent_name=tc.name,
                        output_data=result if "error" not in result else None,
                        error=result.get("error"),
                    ),
                )
                await message_repo.create(conn, tool_result_msg)
                await conn.commit()

                tool_result_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": json.dumps(result),
                    }
                )

            # Add tool results as user message (Anthropic API convention)
            chat_messages.append(ChatMessage(role="user", content=tool_result_blocks))

        # Exhausted max rounds — return a fallback message
        logger.warning(
            "Orchestration loop hit max rounds (%d) for conversation %s",
            _MAX_TOOL_ROUNDS,
            conversation_id,
        )
        fallback = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="I've reached the maximum number of steps for this request. "
            "Here's what I've done so far — please let me know how to continue.",
        )
        fallback = await message_repo.create(conn, fallback)
        await conn.commit()
        return fallback

    async def _get_llm_client(
        self,
        agent: AgentDefinition,
        conn: AsyncConnection,
    ) -> LLMClient:
        """Resolve the LLM client for the given agent's model provider."""
        return await self._llm_client_factory(agent.model_provider, conn)

    async def _resolve_credential_values(self, agent: AgentDefinition) -> list[str]:
        """Resolve credential string values for security inspection."""
        if not agent.credentials or self._credential_store is None:
            return []
        values = []
        for ref in agent.credentials:
            cred = await self._credential_store.get_credential(ref)
            values.append(cred.value)
        return values


def _messages_to_chat(messages: list[Message]) -> list[ChatMessage]:
    """Convert persisted messages to ChatMessage format for the LLM."""
    chat: list[ChatMessage] = []
    for msg in messages:
        if msg.role == MessageRole.USER:
            chat.append(ChatMessage(role="user", content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            if msg.tool_calls:
                # Reconstruct assistant content with tool_use blocks
                content: list[dict] = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.agent_name,
                            "input": tc.input_data,
                        }
                    )
                chat.append(ChatMessage(role="assistant", content=content))
            else:
                chat.append(ChatMessage(role="assistant", content=msg.content))
        elif msg.role == MessageRole.TOOL_RESULT:
            if msg.tool_result:
                block = {
                    "type": "tool_result",
                    "tool_use_id": msg.tool_result.tool_call_id,
                    "content": msg.content,
                }
                # Tool results should be grouped as a user message.
                # Check if the last chat message is already a user message with tool results.
                if chat and chat[-1].role == "user" and isinstance(chat[-1].content, list):
                    chat[-1].content.append(block)
                else:
                    chat.append(ChatMessage(role="user", content=[block]))
    return chat
