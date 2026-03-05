import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  listAgents,
  listConversations,
  getConversation,
  createConversation,
  sendMessage,
  deleteConversation,
} from "../api/client";
import type {
  Agent,
  Conversation,
  Message,
} from "../api/types";

export function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Orchestrator selection
  const [orchestrators, setOrchestrators] = useState<Agent[]>([]);
  const [selectedOrchestratorId, setSelectedOrchestratorId] = useState<string | null>(
    searchParams.get("orchestrator"),
  );

  // Conversations
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  // Messages
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load orchestrator agents on mount
  useEffect(() => {
    listAgents()
      .then((res) => {
        const orch = res.agents.filter((a) => a.is_orchestrator);
        setOrchestrators(orch);
        // Auto-select if only one, or if URL param matches
        if (orch.length > 0 && !selectedOrchestratorId) {
          setSelectedOrchestratorId(orch[0].id);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync orchestrator ID to URL
  useEffect(() => {
    if (selectedOrchestratorId) {
      setSearchParams({ orchestrator: selectedOrchestratorId }, { replace: true });
    }
  }, [selectedOrchestratorId, setSearchParams]);

  // Load conversations when orchestrator changes
  useEffect(() => {
    if (!selectedOrchestratorId) {
      setConversations([]);
      return;
    }
    listConversations(selectedOrchestratorId)
      .then((res) => setConversations(res.conversations))
      .catch((err) => setError(err.message));
  }, [selectedOrchestratorId]);

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    getConversation(activeConversationId)
      .then((res) => setMessages(res.messages))
      .catch((err) => setError(err.message));
  }, [activeConversationId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function handleCreateConversation() {
    if (!selectedOrchestratorId) return;
    try {
      const conv = await createConversation({
        orchestrator_agent_id: selectedOrchestratorId,
        title: "",
      });
      setConversations((prev) => [conv, ...prev]);
      setActiveConversationId(conv.id);
      setMessages([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDeleteConversation(id: string) {
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        setActiveConversationId(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleSend() {
    if (!inputText.trim() || !activeConversationId || sending) return;

    const text = inputText.trim();
    setInputText("");
    setSending(true);
    setError(null);

    // Optimistic user message
    const optimisticMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversationId,
      role: "user",
      content: text,
      tool_calls: null,
      tool_result: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    try {
      await sendMessage(activeConversationId, text);
      // Re-fetch full conversation to get all messages including tool use/result
      const detail = await getConversation(activeConversationId);
      setMessages(detail.messages);
      // Update conversation in list (title may have changed)
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConversationId
            ? { ...c, title: detail.title, updated_at: detail.updated_at }
            : c,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== optimisticMsg.id));
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function toggleToolExpanded(messageId: string) {
    setExpandedTools((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  }

  function formatDate(iso: string) {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (orchestrators.length === 0) {
    return (
      <div className="empty-state">
        <p>No orchestrator agents found.</p>
        <p>
          Create an agent with <strong>is_orchestrator</strong> enabled to start chatting.
        </p>
        <Link to="/agents/new" className="btn btn-primary">
          Create Agent
        </Link>
      </div>
    );
  }

  return (
    <div className="chat-page">
      {/* Left panel: orchestrator selector + conversation list */}
      <div className="chat-sidebar">
        <div className="chat-sidebar-header">
          <select
            className="form-select"
            value={selectedOrchestratorId ?? ""}
            onChange={(e) => {
              setSelectedOrchestratorId(e.target.value || null);
              setActiveConversationId(null);
              setMessages([]);
            }}
          >
            {orchestrators.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleCreateConversation}
            disabled={!selectedOrchestratorId}
            style={{ width: "100%" }}
          >
            New Conversation
          </button>
        </div>
        <ul className="chat-conversation-list">
          {conversations.map((conv) => (
            <li
              key={conv.id}
              className={`chat-conversation-item${
                conv.id === activeConversationId ? " active" : ""
              }`}
              onClick={() => setActiveConversationId(conv.id)}
            >
              <span className="chat-conversation-title">
                {conv.title || "Untitled"}
              </span>
              <span className="chat-conversation-meta">
                <span className="chat-conversation-date">
                  {formatDate(conv.updated_at)}
                </span>
                <button
                  className="chat-conversation-delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteConversation(conv.id);
                  }}
                  title="Delete conversation"
                >
                  &times;
                </button>
              </span>
            </li>
          ))}
          {conversations.length === 0 && (
            <li className="chat-conversation-empty">No conversations yet</li>
          )}
        </ul>
      </div>

      {/* Right panel: messages + input */}
      <div className="chat-main">
        {error && (
          <div className="error" style={{ margin: "1rem 1.5rem 0" }}>
            {error}
          </div>
        )}

        {!activeConversationId ? (
          <div className="chat-empty-state">
            Select or create a conversation to begin.
          </div>
        ) : (
          <>
            <div className="chat-messages">
              {messages.map((msg) => renderMessage(msg))}
              {sending && (
                <div className="chat-thinking">
                  <span className="chat-thinking-dots">
                    Thinking<span>.</span><span>.</span><span>.</span>
                  </span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="chat-input-bar">
              <textarea
                ref={inputRef}
                className="chat-input"
                placeholder="Type a message..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={sending}
                rows={1}
              />
              <button
                className="btn btn-primary"
                onClick={handleSend}
                disabled={sending || !inputText.trim()}
              >
                Send
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );

  function renderMessage(msg: Message) {
    if (msg.role === "user") {
      return (
        <div key={msg.id} className="chat-message chat-message-user">
          {msg.content}
        </div>
      );
    }

    if (msg.role === "assistant") {
      return (
        <div key={msg.id} className="chat-message chat-message-assistant">
          {msg.content && (
            <div className="chat-message-content">{msg.content}</div>
          )}
          {msg.tool_calls && msg.tool_calls.length > 0 && (
            <div className="chat-tool-calls">
              <button
                className="chat-tool-toggle"
                onClick={() => toggleToolExpanded(msg.id)}
              >
                {expandedTools.has(msg.id) ? "\u25BC" : "\u25B6"}{" "}
                {msg.tool_calls.length} tool call
                {msg.tool_calls.length > 1 ? "s" : ""}
              </button>
              {expandedTools.has(msg.id) &&
                msg.tool_calls.map((tc) => (
                  <div key={tc.id} className="chat-tool-detail">
                    <div className="chat-tool-name">{tc.agent_name}</div>
                    <pre>{JSON.stringify(tc.input_data, null, 2)}</pre>
                  </div>
                ))}
            </div>
          )}
        </div>
      );
    }

    if (msg.role === "tool_result" && msg.tool_result) {
      const tr = msg.tool_result;
      const isExpanded = expandedTools.has(msg.id);
      return (
        <div key={msg.id} className="chat-message chat-message-tool">
          <button
            className="chat-tool-toggle"
            onClick={() => toggleToolExpanded(msg.id)}
          >
            {isExpanded ? "\u25BC" : "\u25B6"} {tr.agent_name}
            {tr.error ? " (error)" : " (result)"}
          </button>
          {isExpanded && (
            <div className="chat-tool-detail">
              {tr.error ? (
                <pre className="chat-tool-error">{tr.error}</pre>
              ) : (
                <pre>{JSON.stringify(tr.output_data, null, 2)}</pre>
              )}
            </div>
          )}
        </div>
      );
    }

    // tool_use messages are typically represented in the assistant message's tool_calls
    // so we skip rendering them separately to avoid duplication
    return null;
  }
}
