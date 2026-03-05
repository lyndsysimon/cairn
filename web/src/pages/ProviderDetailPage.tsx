import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  getProvider,
  updateProvider,
  deleteProvider,
  discoverProviderModels,
} from "../api/client";
import type { ModelProvider, ModelConfig } from "../api/types";

export function ProviderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [provider, setProvider] = useState<ModelProvider | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const [editName, setEditName] = useState("");
  const [editProviderType, setEditProviderType] = useState("");
  const [editApiBaseUrl, setEditApiBaseUrl] = useState("");
  const [editApiKeyCredentialId, setEditApiKeyCredentialId] = useState("");
  const [editIsEnabled, setEditIsEnabled] = useState(true);
  const [editModels, setEditModels] = useState<ModelConfig[]>([]);

  const [newModelId, setNewModelId] = useState("");
  const [newModelDisplayName, setNewModelDisplayName] = useState("");
  const [fetchingModels, setFetchingModels] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getProvider(id)
      .then((p) => {
        setProvider(p);
        populateEditFields(p);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  function populateEditFields(p: ModelProvider) {
    setEditName(p.name);
    setEditProviderType(p.provider_type);
    setEditApiBaseUrl(p.api_base_url || "");
    setEditApiKeyCredentialId(p.api_key_credential_id || "");
    setEditIsEnabled(p.is_enabled);
    setEditModels(p.models.map((m) => ({ ...m })));
  }

  async function handleFetchModels() {
    if (!id) return;
    setFetchingModels(true);
    setError(null);
    try {
      const result = await discoverProviderModels(id);
      setEditModels((prev) => {
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

  function addModel() {
    if (!newModelId.trim() || !newModelDisplayName.trim()) return;
    setEditModels((prev) => [
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

  function removeModel(index: number) {
    setEditModels((prev) => prev.filter((_, i) => i !== index));
  }

  function toggleModel(index: number) {
    setEditModels((prev) =>
      prev.map((m, i) =>
        i === index ? { ...m, is_enabled: !m.is_enabled } : m,
      ),
    );
  }

  async function handleSave() {
    if (!id) return;
    try {
      const updated = await updateProvider(id, {
        name: editName,
        provider_type: editProviderType,
        api_base_url: editApiBaseUrl || null,
        api_key_credential_id: editApiKeyCredentialId || null,
        is_enabled: editIsEnabled,
        models: editModels,
      });
      setProvider(updated);
      setEditing(false);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleDelete() {
    if (!id || !provider) return;
    if (!confirm(`Delete provider "${provider.name}"?`)) return;
    try {
      await deleteProvider(id);
      navigate("/providers");
    } catch (e) {
      setError(String(e));
    }
  }

  if (loading) return <div className="loading">Loading...</div>;
  if (error && !provider) return <div className="error">{error}</div>;
  if (!provider) return <div className="error">Provider not found</div>;

  return (
    <>
      <div className="page-header">
        <h1>{editing ? "Edit Provider" : provider.name}</h1>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {!editing && (
            <>
              <button className="btn" onClick={() => setEditing(true)}>
                Edit
              </button>
              <button className="btn btn-danger" onClick={handleDelete}>
                Delete
              </button>
            </>
          )}
          <Link to="/providers" className="btn">
            Back
          </Link>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

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
            <label className="form-label">Provider Type</label>
            <input
              className="form-input"
              value={editProviderType}
              onChange={(e) => setEditProviderType(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">API Base URL</label>
            <input
              className="form-input"
              value={editApiBaseUrl}
              onChange={(e) => setEditApiBaseUrl(e.target.value)}
              placeholder="https://api.anthropic.com"
            />
          </div>
          <div className="form-group">
            <label className="form-label">API Key Credential ID</label>
            <input
              className="form-input"
              value={editApiKeyCredentialId}
              onChange={(e) => setEditApiKeyCredentialId(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">
              <input
                type="checkbox"
                checked={editIsEnabled}
                onChange={(e) => setEditIsEnabled(e.target.checked)}
                style={{ marginRight: "0.5rem" }}
              />
              Enabled
            </label>
          </div>

          <div className="form-group">
            <label className="form-label">Models</label>
            {provider?.supports_model_discovery && (
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
                  Add models from the provider API (new ones only)
                </span>
              </div>
            )}
            {editModels.length > 0 && (
              <table
                className="agent-table"
                style={{ marginBottom: "0.75rem" }}
              >
                <thead>
                  <tr>
                    <th>Model ID</th>
                    <th>Display Name</th>
                    <th>Enabled</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {editModels.map((model, index) => (
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
                  placeholder="Model ID"
                />
              </div>
              <div
                className="form-group"
                style={{
                  display: "flex",
                  flexDirection: "row",
                  gap: "0.5rem",
                }}
              >
                <input
                  className="form-input"
                  value={newModelDisplayName}
                  onChange={(e) => setNewModelDisplayName(e.target.value)}
                  placeholder="Display Name"
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn"
                  onClick={addModel}
                  disabled={
                    !newModelId.trim() || !newModelDisplayName.trim()
                  }
                >
                  Add
                </button>
              </div>
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              Save
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => {
                setEditing(false);
                if (provider) populateEditFields(provider);
              }}
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
                  className={`status ${provider.is_enabled ? "status-active" : "status-inactive"}`}
                >
                  {provider.is_enabled ? "enabled" : "disabled"}
                </span>
              </span>
              <span className="detail-label">Provider Type</span>
              <span className="detail-value">
                <code>{provider.provider_type}</code>
              </span>
              <span className="detail-label">Created</span>
              <span className="detail-value">
                {new Date(provider.created_at).toLocaleString()}
              </span>
              <span className="detail-label">Updated</span>
              <span className="detail-value">
                {new Date(provider.updated_at).toLocaleString()}
              </span>
            </div>
          </div>

          <div className="detail-section">
            <h2>Configuration</h2>
            <div className="detail-grid">
              <span className="detail-label">API Base URL</span>
              <span className="detail-value">
                {provider.api_base_url ? (
                  <code>{provider.api_base_url}</code>
                ) : (
                  "Default"
                )}
              </span>
              <span className="detail-label">API Key</span>
              <span className="detail-value">
                {provider.api_key_credential_id ? (
                  <code>{provider.api_key_credential_id}</code>
                ) : (
                  "Not configured"
                )}
              </span>
            </div>
          </div>

          <div className="detail-section">
            <h2>Models ({provider.models.length})</h2>
            {provider.models.length === 0 ? (
              <p style={{ color: "var(--color-text-secondary)", fontSize: "0.875rem" }}>
                No models configured.
              </p>
            ) : (
              <table className="agent-table">
                <thead>
                  <tr>
                    <th>Model ID</th>
                    <th>Display Name</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {provider.models.map((model, index) => (
                    <tr key={index}>
                      <td>
                        <code>{model.model_id}</code>
                      </td>
                      <td>{model.display_name}</td>
                      <td>
                        <span
                          className={`status ${model.is_enabled ? "status-active" : "status-inactive"}`}
                        >
                          {model.is_enabled ? "enabled" : "disabled"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </>
  );
}
