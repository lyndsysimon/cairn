import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  getAgent,
  updateAgent,
  deleteAgent,
  listRuns,
  createRun,
  listProviders,
  listCredentials,
  listAgents,
  listTools,
} from "../api/client";
import type {
  Agent,
  AgentRun,
  AgentStatus,
  Credential,
  ModelProvider,
  RunStatus,
  RuntimeType,
  Tool,
  TriggerType,
} from "../api/types";

const RUNTIME_TYPES: RuntimeType[] = [
  "docker",
  "podman",
  "apple_container",
  "aws_lambda",
];

const TRIGGER_TYPES: TriggerType[] = [
  "manual",
  "scheduled",
  "webhook",
  "agent_to_agent",
];

const RUN_STATUSES: RunStatus[] = [
  "pending",
  "running",
  "completed",
  "failed",
  "cancelled",
];

function RunStatusBadge({ status }: { status: string }) {
  const classMap: Record<string, string> = {
    completed: "status-active",
    running: "status-running",
    pending: "status-inactive",
    failed: "status-error",
    cancelled: "status-inactive",
  };
  return (
    <span className={`status ${classMap[status] ?? "status-inactive"}`}>
      {status}
    </span>
  );
}

export function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  // Edit state
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editSystemPrompt, setEditSystemPrompt] = useState("");
  const [editStatus, setEditStatus] = useState<AgentStatus>("active");
  const [editIsOrchestrator, setEditIsOrchestrator] = useState(false);
  const [editModelProvider, setEditModelProvider] = useState("");
  const [editModelName, setEditModelName] = useState("");
  const [editTriggerType, setEditTriggerType] =
    useState<TriggerType>("manual");
  const [editCronExpression, setEditCronExpression] = useState("0 * * * *");
  const [editTimezone, setEditTimezone] = useState("UTC");
  const [editWebhookPath, setEditWebhookPath] = useState("");
  const [editSourceAgentIds, setEditSourceAgentIds] = useState<string[]>([]);
  const [editRuntimeType, setEditRuntimeType] =
    useState<RuntimeType>("docker");
  const [editRuntimeImage, setEditRuntimeImage] = useState("python:3.13-slim");
  const [editTimeoutSeconds, setEditTimeoutSeconds] = useState(300);
  const [editMemoryLimitMb, setEditMemoryLimitMb] = useState(512);
  const [editEnvVars, setEditEnvVars] = useState<
    { key: string; value: string }[]
  >([]);
  const [editInputSchema, setEditInputSchema] = useState(
    '{"type": "object"}',
  );
  const [editOutputSchema, setEditOutputSchema] = useState(
    '{"type": "object"}',
  );
  const [editCredentials, setEditCredentials] = useState<
    { credential_id: string; env_var_name: string }[]
  >([]);
  const [editToolIds, setEditToolIds] = useState<string[]>([]);

  // Reference data for edit mode
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [availableCredentials, setAvailableCredentials] = useState<
    Credential[]
  >([]);
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [availableTools, setAvailableTools] = useState<Tool[]>([]);

  // Runs
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [runStatusFilter, setRunStatusFilter] = useState<string>("");
  const [triggering, setTriggering] = useState(false);
  const [showRunInput, setShowRunInput] = useState(false);
  const [runInput, setRunInput] = useState("{}");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getAgent(id)
      .then((a) => {
        setAgent(a);
        populateEditState(a);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));

    loadRuns(id);
  }, [id]);

  useEffect(() => {
    if (!id) return;
    loadRuns(id, runStatusFilter || undefined);
  }, [runStatusFilter]);

  function populateEditState(a: Agent) {
    setEditName(a.name);
    setEditDescription(a.description);
    setEditSystemPrompt(a.system_prompt);
    setEditStatus(a.status);
    setEditIsOrchestrator(a.is_orchestrator);
    setEditModelProvider(a.model_provider);
    setEditModelName(a.model_name);
    setEditTriggerType(a.trigger.type);
    if ("cron_expression" in a.trigger) {
      setEditCronExpression(a.trigger.cron_expression);
    }
    if ("timezone" in a.trigger) {
      setEditTimezone(a.trigger.timezone);
    }
    if ("path" in a.trigger) {
      setEditWebhookPath(a.trigger.path);
    }
    if ("source_agent_ids" in a.trigger) {
      setEditSourceAgentIds(a.trigger.source_agent_ids);
    }
    setEditRuntimeType(a.runtime.type);
    setEditRuntimeImage(a.runtime.image ?? "");
    setEditTimeoutSeconds(a.runtime.timeout_seconds);
    setEditMemoryLimitMb(a.runtime.memory_limit_mb);
    setEditEnvVars(
      Object.entries(a.runtime.environment).map(([key, value]) => ({
        key,
        value,
      })),
    );
    setEditInputSchema(JSON.stringify(a.input_schema, null, 2));
    setEditOutputSchema(JSON.stringify(a.output_schema, null, 2));
    setEditCredentials(
      a.credentials.map((c) => ({
        credential_id: c.credential_id,
        env_var_name: c.env_var_name,
      })),
    );
    setEditToolIds(a.tool_ids || []);
  }

  function startEditing() {
    if (agent) populateEditState(agent);
    // Load reference data for dropdowns
    listProviders(true)
      .then((data) => setProviders(data.providers))
      .catch(() => {});
    listCredentials()
      .then((data) => setAvailableCredentials(data.credentials))
      .catch(() => {});
    listAgents()
      .then((data) =>
        setAvailableAgents(data.agents.filter((a) => a.id !== id)),
      )
      .catch(() => {});
    listTools(true)
      .then((data) => setAvailableTools(data.tools))
      .catch(() => {});
    setEditing(true);
  }

  function loadRuns(agentId: string, status?: string) {
    setRunsLoading(true);
    listRuns(agentId, status)
      .then((data) => setRuns(data.runs))
      .catch(() => {})
      .finally(() => setRunsLoading(false));
  }

  async function handleTriggerRun() {
    if (!id) return;
    setTriggering(true);
    try {
      let inputData: Record<string, unknown> | null = null;
      if (runInput.trim() && runInput.trim() !== "{}") {
        inputData = JSON.parse(runInput);
      }
      await createRun(id, { input_data: inputData });
      setShowRunInput(false);
      setRunInput("{}");
      loadRuns(id, runStatusFilter || undefined);
    } catch (e) {
      setError(String(e));
    } finally {
      setTriggering(false);
    }
  }

  async function handleSave() {
    if (!id) return;
    try {
      let trigger: Agent["trigger"];
      switch (editTriggerType) {
        case "manual":
          trigger = { type: "manual" };
          break;
        case "scheduled":
          trigger = {
            type: "scheduled",
            cron_expression: editCronExpression,
            timezone: editTimezone,
          };
          break;
        case "webhook":
          trigger = { type: "webhook", path: editWebhookPath };
          break;
        case "agent_to_agent":
          trigger = {
            type: "agent_to_agent",
            source_agent_ids: editSourceAgentIds,
          };
          break;
      }

      const environment: Record<string, string> = {};
      for (const ev of editEnvVars) {
        if (ev.key.trim()) environment[ev.key.trim()] = ev.value;
      }

      const updated = await updateAgent(id, {
        name: editName,
        description: editDescription,
        system_prompt: editSystemPrompt,
        status: editStatus,
        is_orchestrator: editIsOrchestrator,
        model_provider: editModelProvider,
        model_name: editModelName,
        trigger,
        runtime: {
          type: editRuntimeType,
          image: editRuntimeImage || null,
          timeout_seconds: editTimeoutSeconds,
          memory_limit_mb: editMemoryLimitMb,
          environment,
        },
        input_schema: JSON.parse(editInputSchema),
        output_schema: JSON.parse(editOutputSchema),
        credentials: editCredentials
          .filter((c) => c.credential_id && c.env_var_name)
          .map((c) => ({
            store_name: "postgres",
            credential_id: c.credential_id,
            env_var_name: c.env_var_name,
          })),
        tool_ids: editToolIds,
      });
      setAgent(updated);
      setEditing(false);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleDelete() {
    if (!id || !agent) return;
    if (!confirm(`Delete agent "${agent.name}"?`)) return;
    try {
      await deleteAgent(id);
      navigate("/");
    } catch (e) {
      setError(String(e));
    }
  }

  if (loading) return <div className="loading">Loading...</div>;
  if (error && !agent) return <div className="error">{error}</div>;
  if (!agent) return <div className="error">Agent not found</div>;

  return (
    <>
      <div className="page-header">
        <h1>{editing ? "Edit Agent" : agent.name}</h1>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {!editing && (
            <>
              <button
                className="btn btn-primary"
                onClick={() => setShowRunInput(!showRunInput)}
              >
                Run
              </button>
              <button className="btn" onClick={startEditing}>
                Edit
              </button>
              <button className="btn btn-danger" onClick={handleDelete}>
                Delete
              </button>
            </>
          )}
          <Link to="/" className="btn">
            Back
          </Link>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {showRunInput && !editing && (
        <div className="detail-section" style={{ marginBottom: "1rem" }}>
          <h2>Trigger Run</h2>
          <div className="form" style={{ maxWidth: "none" }}>
            <div className="form-group">
              <label className="form-label">Input Data (JSON)</label>
              <textarea
                className="form-textarea"
                value={runInput}
                onChange={(e) => setRunInput(e.target.value)}
                rows={3}
              />
            </div>
            <div className="form-actions">
              <button
                className="btn btn-primary"
                onClick={handleTriggerRun}
                disabled={triggering}
              >
                {triggering ? "Triggering..." : "Trigger"}
              </button>
              <button
                className="btn"
                onClick={() => setShowRunInput(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {editing ? (
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            handleSave();
          }}
        >
          <div className="form-group">
            <label className="form-label">Name</label>
            <input
              className="form-input"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Description</label>
            <input
              className="form-input"
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Status</label>
            <select
              className="form-select"
              value={editStatus}
              onChange={(e) =>
                setEditStatus(e.target.value as AgentStatus)
              }
            >
              <option value="active">active</option>
              <option value="inactive">inactive</option>
            </select>
          </div>

          {/* Model */}
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Model Provider</label>
              {providers.length > 0 ? (
                <select
                  className="form-select"
                  value={editModelProvider}
                  onChange={(e) => {
                    setEditModelProvider(e.target.value);
                    setEditModelName("");
                  }}
                  required
                >
                  <option value="">Select a provider...</option>
                  {providers.map((p) => (
                    <option key={p.id} value={p.provider_type}>
                      {p.name}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="form-input"
                  value={editModelProvider}
                  onChange={(e) => setEditModelProvider(e.target.value)}
                  required
                />
              )}
            </div>
            <div className="form-group">
              <label className="form-label">Model Name</label>
              {(() => {
                const selectedProvider = providers.find(
                  (p) => p.provider_type === editModelProvider,
                );
                const enabledModels =
                  selectedProvider?.models.filter((m) => m.is_enabled) ??
                  [];
                if (enabledModels.length > 0) {
                  return (
                    <select
                      className="form-select"
                      value={editModelName}
                      onChange={(e) => setEditModelName(e.target.value)}
                      required
                    >
                      <option value="">Select a model...</option>
                      {enabledModels.map((m) => (
                        <option key={m.model_id} value={m.model_id}>
                          {m.display_name}
                        </option>
                      ))}
                    </select>
                  );
                }
                return (
                  <input
                    className="form-input"
                    value={editModelName}
                    onChange={(e) => setEditModelName(e.target.value)}
                    required
                  />
                );
              })()}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">System Prompt</label>
            <textarea
              className="form-textarea"
              value={editSystemPrompt}
              onChange={(e) => setEditSystemPrompt(e.target.value)}
              rows={4}
            />
          </div>

          <div className="form-group">
            <label className="form-checkbox-label">
              <input
                type="checkbox"
                checked={editIsOrchestrator}
                onChange={(e) => setEditIsOrchestrator(e.target.checked)}
              />
              Orchestrator agent
            </label>
            <span className="form-hint">
              Orchestrator agents delegate work to other agents via tool calls
              and are accessible from the Chat page.
            </span>
          </div>

          {/* Trigger */}
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Trigger</label>
              <select
                className="form-select"
                value={editTriggerType}
                onChange={(e) =>
                  setEditTriggerType(e.target.value as TriggerType)
                }
              >
                {TRIGGER_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            {editTriggerType === "scheduled" && (
              <div className="form-group">
                <label className="form-label">Cron Expression</label>
                <input
                  className="form-input"
                  value={editCronExpression}
                  onChange={(e) => setEditCronExpression(e.target.value)}
                  placeholder="0 * * * *"
                />
              </div>
            )}
            {editTriggerType === "webhook" && (
              <div className="form-group">
                <label className="form-label">Webhook Path</label>
                <input
                  className="form-input"
                  value={editWebhookPath}
                  onChange={(e) => setEditWebhookPath(e.target.value)}
                  placeholder="/hooks/my-agent"
                />
              </div>
            )}
          </div>
          {editTriggerType === "scheduled" && (
            <div className="form-group">
              <label className="form-label">Timezone</label>
              <input
                className="form-input"
                value={editTimezone}
                onChange={(e) => setEditTimezone(e.target.value)}
                placeholder="UTC"
              />
              <span className="form-hint">
                IANA timezone (e.g. America/New_York, Europe/London)
              </span>
            </div>
          )}
          {editTriggerType === "agent_to_agent" && (
            <div className="form-group">
              <label className="form-label">Source Agents</label>
              {availableAgents.length > 0 ? (
                <select
                  className="form-select"
                  multiple
                  value={editSourceAgentIds}
                  onChange={(e) =>
                    setEditSourceAgentIds(
                      Array.from(
                        e.target.selectedOptions,
                        (o) => o.value,
                      ),
                    )
                  }
                  style={{ minHeight: "80px" }}
                >
                  {availableAgents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="form-hint">
                  No other agents available.
                </span>
              )}
              <span className="form-hint">
                Hold Ctrl/Cmd to select multiple agents
              </span>
            </div>
          )}

          {/* Runtime */}
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Runtime</label>
              <select
                className="form-select"
                value={editRuntimeType}
                onChange={(e) =>
                  setEditRuntimeType(e.target.value as RuntimeType)
                }
              >
                {RUNTIME_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Container Image</label>
              <input
                className="form-input"
                value={editRuntimeImage}
                onChange={(e) => setEditRuntimeImage(e.target.value)}
                placeholder="python:3.13-slim"
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Timeout (seconds)</label>
              <input
                className="form-input"
                type="number"
                min={1}
                value={editTimeoutSeconds}
                onChange={(e) =>
                  setEditTimeoutSeconds(Number(e.target.value))
                }
              />
            </div>
            <div className="form-group">
              <label className="form-label">Memory Limit (MB)</label>
              <input
                className="form-input"
                type="number"
                min={64}
                value={editMemoryLimitMb}
                onChange={(e) =>
                  setEditMemoryLimitMb(Number(e.target.value))
                }
              />
            </div>
          </div>

          {/* Environment Variables */}
          <div className="form-group">
            <label className="form-label">Environment Variables</label>
            {editEnvVars.map((ev, i) => (
              <div
                key={i}
                className="form-row"
                style={{ marginBottom: "0.5rem" }}
              >
                <input
                  className="form-input"
                  value={ev.key}
                  onChange={(e) => {
                    const next = [...editEnvVars];
                    next[i] = { ...next[i], key: e.target.value };
                    setEditEnvVars(next);
                  }}
                  placeholder="KEY"
                />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    className="form-input"
                    value={ev.value}
                    onChange={(e) => {
                      const next = [...editEnvVars];
                      next[i] = { ...next[i], value: e.target.value };
                      setEditEnvVars(next);
                    }}
                    placeholder="value"
                    style={{ flex: 1 }}
                  />
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() =>
                      setEditEnvVars((prev) =>
                        prev.filter((_, j) => j !== i),
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
            <button
              type="button"
              className="btn btn-sm"
              onClick={() =>
                setEditEnvVars((prev) => [
                  ...prev,
                  { key: "", value: "" },
                ])
              }
            >
              + Add Variable
            </button>
          </div>

          {/* Credentials */}
          <div className="form-group">
            <label className="form-label">Credentials</label>
            {editCredentials.map((sc, i) => (
              <div
                key={i}
                className="form-row"
                style={{ marginBottom: "0.5rem" }}
              >
                <select
                  className="form-select"
                  value={sc.credential_id}
                  onChange={(e) => {
                    const next = [...editCredentials];
                    next[i] = {
                      ...next[i],
                      credential_id: e.target.value,
                    };
                    setEditCredentials(next);
                  }}
                >
                  <option value="">Select credential...</option>
                  {availableCredentials.map((c) => (
                    <option key={c.id} value={c.credential_id}>
                      {c.credential_id}
                    </option>
                  ))}
                </select>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    className="form-input"
                    value={sc.env_var_name}
                    onChange={(e) => {
                      const next = [...editCredentials];
                      next[i] = {
                        ...next[i],
                        env_var_name: e.target.value,
                      };
                      setEditCredentials(next);
                    }}
                    placeholder="ENV_VAR_NAME"
                    style={{ flex: 1 }}
                  />
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() =>
                      setEditCredentials((prev) =>
                        prev.filter((_, j) => j !== i),
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
            <button
              type="button"
              className="btn btn-sm"
              onClick={() =>
                setEditCredentials((prev) => [
                  ...prev,
                  { credential_id: "", env_var_name: "" },
                ])
              }
            >
              + Add Credential
            </button>
            <span className="form-hint">
              Map credentials to environment variables in the agent
              runtime
            </span>
          </div>

          {/* Tools */}
          <div className="form-group">
            <label className="form-label">Tools</label>
            {availableTools.length > 0 ? (
              <>
                {availableTools.map((tool) => (
                  <label
                    key={tool.id}
                    className="form-checkbox-label"
                    style={{ display: "block", marginBottom: "0.25rem" }}
                  >
                    <input
                      type="checkbox"
                      checked={editToolIds.includes(tool.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setEditToolIds((prev) => [...prev, tool.id]);
                        } else {
                          setEditToolIds((prev) =>
                            prev.filter((tid) => tid !== tool.id),
                          );
                        }
                      }}
                    />
                    {tool.display_name}
                    {!tool.is_sandbox_safe && (
                      <span
                        className="status status-error"
                        style={{
                          marginLeft: "0.5rem",
                          fontSize: "0.75rem",
                        }}
                      >
                        external
                      </span>
                    )}
                  </label>
                ))}
              </>
            ) : (
              <span className="form-hint">No tools available.</span>
            )}
            <span className="form-hint">
              Select tools this agent can use during execution
            </span>
          </div>

          {/* Schemas */}
          <div className="form-group">
            <label className="form-label">Input Schema (JSON)</label>
            <textarea
              className="form-textarea"
              value={editInputSchema}
              onChange={(e) => setEditInputSchema(e.target.value)}
              rows={3}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Output Schema (JSON)</label>
            <textarea
              className="form-textarea"
              value={editOutputSchema}
              onChange={(e) => setEditOutputSchema(e.target.value)}
              rows={3}
            />
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              Save
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => setEditing(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <>
          <div className="detail-section">
            <h2>Overview</h2>
            <div className="detail-grid">
              <span className="detail-label">Status</span>
              <span className="detail-value">
                <span
                  className={`status ${agent.status === "active" ? "status-active" : agent.status === "error" ? "status-error" : "status-inactive"}`}
                >
                  {agent.status}
                </span>
              </span>
              <span className="detail-label">Type</span>
              <span className="detail-value">
                {agent.is_orchestrator ? "Orchestrator" : "Sub-agent"}
              </span>
              <span className="detail-label">Description</span>
              <span className="detail-value">
                {agent.description || "—"}
              </span>
              <span className="detail-label">Created</span>
              <span className="detail-value">
                {new Date(agent.created_at).toLocaleString()}
              </span>
              <span className="detail-label">Updated</span>
              <span className="detail-value">
                {new Date(agent.updated_at).toLocaleString()}
              </span>
            </div>
          </div>

          <div className="detail-section">
            <h2>Model</h2>
            <div className="detail-grid">
              <span className="detail-label">Provider</span>
              <span className="detail-value">
                <code>{agent.model_provider}</code>
              </span>
              <span className="detail-label">Model</span>
              <span className="detail-value">
                <code>{agent.model_name}</code>
              </span>
            </div>
          </div>

          {agent.system_prompt && (
            <div className="detail-section">
              <h2>System Prompt</h2>
              <pre className="detail-code">{agent.system_prompt}</pre>
            </div>
          )}

          <div className="detail-section">
            <h2>Trigger</h2>
            <div className="detail-grid">
              <span className="detail-label">Type</span>
              <span className="detail-value">
                <code>{agent.trigger.type}</code>
              </span>
              {"cron_expression" in agent.trigger && (
                <>
                  <span className="detail-label">Cron</span>
                  <span className="detail-value">
                    <code>{agent.trigger.cron_expression}</code>
                  </span>
                </>
              )}
              {"timezone" in agent.trigger && (
                <>
                  <span className="detail-label">Timezone</span>
                  <span className="detail-value">
                    {agent.trigger.timezone}
                  </span>
                </>
              )}
              {"path" in agent.trigger && (
                <>
                  <span className="detail-label">Path</span>
                  <span className="detail-value">
                    <code>{agent.trigger.path}</code>
                  </span>
                </>
              )}
              {"source_agent_ids" in agent.trigger && (
                <>
                  <span className="detail-label">Source Agents</span>
                  <span className="detail-value">
                    {agent.trigger.source_agent_ids.length > 0
                      ? agent.trigger.source_agent_ids.join(", ")
                      : "—"}
                  </span>
                </>
              )}
            </div>
          </div>

          <div className="detail-section">
            <h2>Runtime</h2>
            <div className="detail-grid">
              <span className="detail-label">Type</span>
              <span className="detail-value">
                <code>{agent.runtime.type}</code>
              </span>
              {agent.runtime.image && (
                <>
                  <span className="detail-label">Image</span>
                  <span className="detail-value">
                    <code>{agent.runtime.image}</code>
                  </span>
                </>
              )}
              <span className="detail-label">Timeout</span>
              <span className="detail-value">
                {agent.runtime.timeout_seconds}s
              </span>
              <span className="detail-label">Memory</span>
              <span className="detail-value">
                {agent.runtime.memory_limit_mb} MB
              </span>
            </div>
            {Object.keys(agent.runtime.environment).length > 0 && (
              <>
                <h3
                  style={{
                    fontSize: "0.875rem",
                    marginTop: "1rem",
                    marginBottom: "0.5rem",
                  }}
                >
                  Environment Variables
                </h3>
                <div className="detail-grid">
                  {Object.entries(agent.runtime.environment).map(
                    ([key, value]) => (
                      <>
                        <span key={`${key}-l`} className="detail-label">
                          <code>{key}</code>
                        </span>
                        <span key={`${key}-v`} className="detail-value">
                          {value}
                        </span>
                      </>
                    ),
                  )}
                </div>
              </>
            )}
          </div>

          {agent.credentials.length > 0 && (
            <div className="detail-section">
              <h2>Credentials</h2>
              <table className="agent-table">
                <thead>
                  <tr>
                    <th>Credential ID</th>
                    <th>Store</th>
                    <th>Env Variable</th>
                  </tr>
                </thead>
                <tbody>
                  {agent.credentials.map((c, i) => (
                    <tr key={i}>
                      <td>
                        <code>{c.credential_id}</code>
                      </td>
                      <td>{c.store_name}</td>
                      <td>
                        <code>{c.env_var_name}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {agent.tool_ids && agent.tool_ids.length > 0 && (
            <div className="detail-section">
              <h2>Tools</h2>
              <p style={{ color: "var(--color-text-secondary)", fontSize: "0.875rem" }}>
                {agent.tool_ids.length} tool{agent.tool_ids.length !== 1 ? "s" : ""} assigned
              </p>
            </div>
          )}

          <div className="detail-section">
            <h2>Input Schema</h2>
            <pre className="detail-code">
              {JSON.stringify(agent.input_schema, null, 2)}
            </pre>
          </div>

          <div className="detail-section">
            <h2>Output Schema</h2>
            <pre className="detail-code">
              {JSON.stringify(agent.output_schema, null, 2)}
            </pre>
          </div>

          <div className="detail-section">
            <h2>
              Run History{" "}
              {!runsLoading && (
                <span
                  style={{
                    fontWeight: 400,
                    textTransform: "none",
                    letterSpacing: 0,
                  }}
                >
                  ({runs.length})
                </span>
              )}
            </h2>
            <div style={{ marginBottom: "0.75rem" }}>
              <select
                className="form-select"
                value={runStatusFilter}
                onChange={(e) => setRunStatusFilter(e.target.value)}
                style={{ width: "auto", minWidth: "160px" }}
              >
                <option value="">All statuses</option>
                {RUN_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            {runsLoading ? (
              <p
                style={{
                  color: "var(--color-text-secondary)",
                  fontSize: "0.875rem",
                }}
              >
                Loading runs...
              </p>
            ) : runs.length === 0 ? (
              <p
                style={{
                  color: "var(--color-text-secondary)",
                  fontSize: "0.875rem",
                }}
              >
                No runs{runStatusFilter ? ` with status "${runStatusFilter}"` : ""}.
              </p>
            ) : (
              <table className="agent-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Duration</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => {
                    let duration = "—";
                    if (run.started_at) {
                      const start = new Date(
                        run.started_at,
                      ).getTime();
                      const end = run.completed_at
                        ? new Date(run.completed_at).getTime()
                        : Date.now();
                      const ms = end - start;
                      duration =
                        ms < 1000
                          ? `${ms}ms`
                          : `${(ms / 1000).toFixed(1)}s`;
                    }
                    return (
                      <tr key={run.id}>
                        <td>
                          <RunStatusBadge status={run.status} />
                        </td>
                        <td>
                          {new Date(
                            run.created_at,
                          ).toLocaleString()}
                        </td>
                        <td>{duration}</td>
                        <td>
                          <Link
                            to={`/runs/${run.id}`}
                            className="btn btn-sm"
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </>
  );
}
