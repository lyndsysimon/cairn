import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { createProvider, discoverModels } from "../api/client";
import type { ModelConfig } from "../api/types";

const PROVIDER_TYPES = [
  "anthropic",
  "openai",
  "openrouter",
  "azure_openai",
  "ollama",
  "bedrock",
  "vertex_ai",
];

const DISCOVERABLE_TYPES = new Set(["openrouter"]);

export function CreateProviderPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState("anthropic");
  const [customProviderType, setCustomProviderType] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [apiKeyCredentialId, setApiKeyCredentialId] = useState("");
  const [isEnabled, setIsEnabled] = useState(true);
  const [models, setModels] = useState<ModelConfig[]>([]);

  const [newModelId, setNewModelId] = useState("");
  const [newModelDisplayName, setNewModelDisplayName] = useState("");
  const [fetchingModels, setFetchingModels] = useState(false);

  function addModel() {
    if (!newModelId.trim() || !newModelDisplayName.trim()) return;
    setModels((prev) => [
      ...prev,
      {
        model_id: newModelId.trim(),
        display_name: newModelDisplayName.trim(),
        is_enabled: true,
      },
    ]);
    setNewModelId("");
    setNewModelDisplayName("");
  }

  async function handleFetchModels() {
    setFetchingModels(true);
    setError(null);
    try {
      const resolvedType =
        providerType === "__custom__" ? customProviderType.trim() : providerType;
      const result = await discoverModels({
        provider_type: resolvedType,
        api_base_url: apiBaseUrl || null,
        api_key_credential_id: apiKeyCredentialId || null,
      });
      // Merge fetched models: add new ones, preserve existing
      setModels((prev) => {
        const existingIds = new Set(prev.map((m) => m.model_id));
        const newModels = result.models.filter((m) => !existingIds.has(m.model_id));
        return [...prev, ...newModels];
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setFetchingModels(false);
    }
  }

  function removeModel(index: number) {
    setModels((prev) => prev.filter((_, i) => i !== index));
  }

  function toggleModel(index: number) {
    setModels((prev) =>
      prev.map((m, i) =>
        i === index ? { ...m, is_enabled: !m.is_enabled } : m,
      ),
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const resolvedType =
        providerType === "__custom__"
          ? customProviderType.trim()
          : providerType;

      if (!resolvedType) {
        setError("Provider type is required");
        setSubmitting(false);
        return;
      }

      const provider = await createProvider({
        name,
        provider_type: resolvedType,
        api_base_url: apiBaseUrl || null,
        api_key_credential_id: apiKeyCredentialId || null,
        models,
        is_enabled: isEnabled,
      });
      navigate(`/providers/${provider.id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>New Provider</h1>
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
            placeholder="Anthropic Production"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Provider Type</label>
            <select
              className="form-select"
              value={providerType}
              onChange={(e) => setProviderType(e.target.value)}
            >
              {PROVIDER_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
              <option value="__custom__">Custom...</option>
            </select>
          </div>
          {providerType === "__custom__" && (
            <div className="form-group">
              <label className="form-label">Custom Type</label>
              <input
                className="form-input"
                value={customProviderType}
                onChange={(e) => setCustomProviderType(e.target.value)}
                placeholder="my_provider"
                required
              />
            </div>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">API Base URL</label>
          <input
            className="form-input"
            value={apiBaseUrl}
            onChange={(e) => setApiBaseUrl(e.target.value)}
            placeholder="https://api.anthropic.com"
          />
          <span className="form-hint">
            Leave empty to use the provider's default URL
          </span>
        </div>

        <div className="form-group">
          <label className="form-label">API Key Credential ID</label>
          <input
            className="form-input"
            value={apiKeyCredentialId}
            onChange={(e) => setApiKeyCredentialId(e.target.value)}
            placeholder="anthropic-api-key"
          />
          <span className="form-hint">
            Reference to a credential in your credential store
          </span>
        </div>

        <div className="form-group">
          <label className="form-label">
            <input
              type="checkbox"
              checked={isEnabled}
              onChange={(e) => setIsEnabled(e.target.checked)}
              style={{ marginRight: "0.5rem" }}
            />
            Enabled
          </label>
        </div>

        <div className="form-group">
          <label className="form-label">Models</label>
          {DISCOVERABLE_TYPES.has(
            providerType === "__custom__" ? customProviderType.trim() : providerType,
          ) && (
            <div style={{ marginBottom: "0.75rem" }}>
              <button
                type="button"
                className="btn"
                onClick={handleFetchModels}
                disabled={fetchingModels}
              >
                {fetchingModels ? "Fetching..." : "Fetch Models"}
              </button>
              <span className="form-hint" style={{ marginLeft: "0.5rem" }}>
                Populate the model list from the provider API
              </span>
            </div>
          )}
          {models.length > 0 && (
            <table className="agent-table" style={{ marginBottom: "0.75rem" }}>
              <thead>
                <tr>
                  <th>Model ID</th>
                  <th>Display Name</th>
                  <th>Enabled</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {models.map((model, index) => (
                  <tr key={index}>
                    <td>
                      <code>{model.model_id}</code>
                    </td>
                    <td>{model.display_name}</td>
                    <td>
                      <input
                        type="checkbox"
                        checked={model.is_enabled}
                        onChange={() => toggleModel(index)}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        onClick={() => removeModel(index)}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="form-row">
            <div className="form-group">
              <input
                className="form-input"
                value={newModelId}
                onChange={(e) => setNewModelId(e.target.value)}
                placeholder="claude-sonnet-4-20250514"
              />
            </div>
            <div
              className="form-group"
              style={{ display: "flex", flexDirection: "row", gap: "0.5rem" }}
            >
              <input
                className="form-input"
                value={newModelDisplayName}
                onChange={(e) => setNewModelDisplayName(e.target.value)}
                placeholder="Claude Sonnet 4"
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="btn"
                onClick={addModel}
                disabled={!newModelId.trim() || !newModelDisplayName.trim()}
              >
                Add
              </button>
            </div>
          </div>
          <span className="form-hint">
            Add models available from this provider
          </span>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
          >
            {submitting ? "Creating..." : "Create Provider"}
          </button>
          <Link to="/providers" className="btn">
            Cancel
          </Link>
        </div>
      </form>
    </>
  );
}
