import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  createAgent,
  listProviders,
  listCredentials,
  listAgents,
} from "../api/client";
import type {
  Agent,
  CreateAgentRequest,
  Credential,
  ModelProvider,
  RuntimeType,
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

export function CreateAgentPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [availableCredentials, setAvailableCredentials] = useState<
    Credential[]
  >([]);
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [modelProvider, setModelProvider] = useState("");
  const [modelName, setModelName] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");

  // Trigger
  const [triggerType, setTriggerType] = useState<TriggerType>("manual");
  const [cronExpression, setCronExpression] = useState("0 * * * *");
  const [timezone, setTimezone] = useState("UTC");
  const [webhookPath, setWebhookPath] = useState("");
  const [sourceAgentIds, setSourceAgentIds] = useState<string[]>([]);

  // Runtime
  const [runtimeType, setRuntimeType] = useState<RuntimeType>("docker");
  const [runtimeImage, setRuntimeImage] = useState("python:3.13-slim");
  const [timeoutSeconds, setTimeoutSeconds] = useState(300);
  const [memoryLimitMb, setMemoryLimitMb] = useState(512);
  const [envVars, setEnvVars] = useState<{ key: string; value: string }[]>(
    [],
  );

  // Schemas
  const [inputSchema, setInputSchema] = useState('{"type": "object"}');
  const [outputSchema, setOutputSchema] = useState('{"type": "object"}');

  // Credentials
  const [selectedCredentials, setSelectedCredentials] = useState<
    { credential_id: string; env_var_name: string }[]
  >([]);

  useEffect(() => {
    listProviders(true)
      .then((data) => setProviders(data.providers))
      .catch(() => {});
    listCredentials()
      .then((data) => setAvailableCredentials(data.credentials))
      .catch(() => {});
    listAgents()
      .then((data) => setAvailableAgents(data.agents))
      .catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      let trigger: CreateAgentRequest["trigger"];
      switch (triggerType) {
        case "manual":
          trigger = { type: "manual" };
          break;
        case "scheduled":
          trigger = {
            type: "scheduled",
            cron_expression: cronExpression,
            timezone,
          };
          break;
        case "webhook":
          trigger = { type: "webhook", path: webhookPath };
          break;
        case "agent_to_agent":
          trigger = {
            type: "agent_to_agent",
            source_agent_ids: sourceAgentIds,
          };
          break;
      }

      const environment: Record<string, string> = {};
      for (const ev of envVars) {
        if (ev.key.trim()) environment[ev.key.trim()] = ev.value;
      }

      const data: CreateAgentRequest = {
        name,
        description,
        model_provider: modelProvider,
        model_name: modelName,
        system_prompt: systemPrompt,
        input_schema: JSON.parse(inputSchema),
        output_schema: JSON.parse(outputSchema),
        trigger,
        runtime: {
          type: runtimeType,
          image: runtimeImage || null,
          timeout_seconds: timeoutSeconds,
          memory_limit_mb: memoryLimitMb,
          environment,
        },
        credentials: selectedCredentials
          .filter((c) => c.credential_id && c.env_var_name)
          .map((c) => ({
            store_name: "postgres",
            credential_id: c.credential_id,
            env_var_name: c.env_var_name,
          })),
      };

      const agent = await createAgent(data);
      navigate(`/agents/${agent.id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>New Agent</h1>
      </div>

      {error && <div className="error">{error}</div>}

      <form className="form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label">Name</label>
          <input
            className="form-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={255}
            placeholder="my-agent"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Description</label>
          <input
            className="form-input"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this agent do?"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Model Provider</label>
            {providers.length > 0 ? (
              <select
                className="form-select"
                value={modelProvider}
                onChange={(e) => {
                  setModelProvider(e.target.value);
                  setModelName("");
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
                value={modelProvider}
                onChange={(e) => setModelProvider(e.target.value)}
                required
                placeholder="anthropic"
              />
            )}
          </div>
          <div className="form-group">
            <label className="form-label">Model Name</label>
            {(() => {
              const selectedProvider = providers.find(
                (p) => p.provider_type === modelProvider,
              );
              const enabledModels =
                selectedProvider?.models.filter((m) => m.is_enabled) ?? [];
              if (enabledModels.length > 0) {
                return (
                  <select
                    className="form-select"
                    value={modelName}
                    onChange={(e) => setModelName(e.target.value)}
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
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  required
                  placeholder="claude-sonnet-4-20250514"
                />
              );
            })()}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">System Prompt</label>
          <textarea
            className="form-textarea"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={3}
            placeholder="You are a helpful assistant."
          />
        </div>

        {/* Trigger */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Trigger</label>
            <select
              className="form-select"
              value={triggerType}
              onChange={(e) =>
                setTriggerType(e.target.value as TriggerType)
              }
            >
              {TRIGGER_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          {triggerType === "scheduled" && (
            <div className="form-group">
              <label className="form-label">Cron Expression</label>
              <input
                className="form-input"
                value={cronExpression}
                onChange={(e) => setCronExpression(e.target.value)}
                placeholder="0 * * * *"
              />
            </div>
          )}
          {triggerType === "webhook" && (
            <div className="form-group">
              <label className="form-label">Webhook Path</label>
              <input
                className="form-input"
                value={webhookPath}
                onChange={(e) => setWebhookPath(e.target.value)}
                placeholder="/hooks/my-agent"
              />
            </div>
          )}
        </div>
        {triggerType === "scheduled" && (
          <div className="form-group">
            <label className="form-label">Timezone</label>
            <input
              className="form-input"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="UTC"
            />
            <span className="form-hint">
              IANA timezone (e.g. America/New_York, Europe/London)
            </span>
          </div>
        )}
        {triggerType === "agent_to_agent" && (
          <div className="form-group">
            <label className="form-label">Source Agents</label>
            {availableAgents.length > 0 ? (
              <select
                className="form-select"
                multiple
                value={sourceAgentIds}
                onChange={(e) =>
                  setSourceAgentIds(
                    Array.from(e.target.selectedOptions, (o) => o.value),
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
                No other agents available. Create agents first.
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
              value={runtimeType}
              onChange={(e) =>
                setRuntimeType(e.target.value as RuntimeType)
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
              value={runtimeImage}
              onChange={(e) => setRuntimeImage(e.target.value)}
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
              value={timeoutSeconds}
              onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Memory Limit (MB)</label>
            <input
              className="form-input"
              type="number"
              min={64}
              value={memoryLimitMb}
              onChange={(e) => setMemoryLimitMb(Number(e.target.value))}
            />
          </div>
        </div>

        {/* Environment Variables */}
        <div className="form-group">
          <label className="form-label">Environment Variables</label>
          {envVars.map((ev, i) => (
            <div
              key={i}
              className="form-row"
              style={{ marginBottom: "0.5rem" }}
            >
              <input
                className="form-input"
                value={ev.key}
                onChange={(e) => {
                  const next = [...envVars];
                  next[i] = { ...next[i], key: e.target.value };
                  setEnvVars(next);
                }}
                placeholder="KEY"
              />
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input
                  className="form-input"
                  value={ev.value}
                  onChange={(e) => {
                    const next = [...envVars];
                    next[i] = { ...next[i], value: e.target.value };
                    setEnvVars(next);
                  }}
                  placeholder="value"
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() =>
                    setEnvVars((prev) => prev.filter((_, j) => j !== i))
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
              setEnvVars((prev) => [...prev, { key: "", value: "" }])
            }
          >
            + Add Variable
          </button>
        </div>

        {/* Credentials */}
        <div className="form-group">
          <label className="form-label">Credentials</label>
          {selectedCredentials.map((sc, i) => (
            <div
              key={i}
              className="form-row"
              style={{ marginBottom: "0.5rem" }}
            >
              <select
                className="form-select"
                value={sc.credential_id}
                onChange={(e) => {
                  const next = [...selectedCredentials];
                  next[i] = { ...next[i], credential_id: e.target.value };
                  setSelectedCredentials(next);
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
                    const next = [...selectedCredentials];
                    next[i] = {
                      ...next[i],
                      env_var_name: e.target.value,
                    };
                    setSelectedCredentials(next);
                  }}
                  placeholder="ENV_VAR_NAME"
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() =>
                    setSelectedCredentials((prev) =>
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
              setSelectedCredentials((prev) => [
                ...prev,
                { credential_id: "", env_var_name: "" },
              ])
            }
          >
            + Add Credential
          </button>
          <span className="form-hint">
            Map credentials to environment variables in the agent runtime
          </span>
        </div>

        {/* Schemas */}
        <div className="form-group">
          <label className="form-label">Input Schema (JSON)</label>
          <textarea
            className="form-textarea"
            value={inputSchema}
            onChange={(e) => setInputSchema(e.target.value)}
            rows={3}
          />
          <span className="form-hint">JSON Schema for agent input</span>
        </div>

        <div className="form-group">
          <label className="form-label">Output Schema (JSON)</label>
          <textarea
            className="form-textarea"
            value={outputSchema}
            onChange={(e) => setOutputSchema(e.target.value)}
            rows={3}
          />
          <span className="form-hint">JSON Schema for agent output</span>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
          >
            {submitting ? "Creating..." : "Create Agent"}
          </button>
          <Link to="/" className="btn">
            Cancel
          </Link>
        </div>
      </form>
    </>
  );
}
