import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { createAgent, listProviders } from "../api/client";
import type {
  CreateAgentRequest,
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

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [modelProvider, setModelProvider] = useState("");
  const [modelName, setModelName] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [triggerType, setTriggerType] = useState<TriggerType>("manual");
  const [cronExpression, setCronExpression] = useState("0 * * * *");
  const [webhookPath, setWebhookPath] = useState("");
  const [runtimeType, setRuntimeType] = useState<RuntimeType>("docker");
  const [runtimeImage, setRuntimeImage] = useState("python:3.13-slim");
  const [inputSchema, setInputSchema] = useState('{"type": "object"}');
  const [outputSchema, setOutputSchema] = useState('{"type": "object"}');

  useEffect(() => {
    listProviders(true)
      .then((data) => setProviders(data.providers))
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
            timezone: "UTC",
          };
          break;
        case "webhook":
          trigger = { type: "webhook", path: webhookPath };
          break;
        case "agent_to_agent":
          trigger = { type: "agent_to_agent", source_agent_ids: [] };
          break;
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
        },
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
