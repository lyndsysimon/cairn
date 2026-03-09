import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getTool, updateTool, deleteTool } from "../api/client";
import type { Tool } from "../api/types";

export function ToolDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tool, setTool] = useState<Tool | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const [editDisplayName, setEditDisplayName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editIsSandboxSafe, setEditIsSandboxSafe] = useState(true);
  const [editParametersSchema, setEditParametersSchema] = useState("");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getTool(id)
      .then((t) => {
        setTool(t);
        populateEditState(t);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  function populateEditState(t: Tool) {
    setEditDisplayName(t.display_name);
    setEditDescription(t.description);
    setEditIsSandboxSafe(t.is_sandbox_safe);
    setEditParametersSchema(JSON.stringify(t.parameters_schema, null, 2));
  }

  function startEditing() {
    if (tool) populateEditState(tool);
    setEditing(true);
  }

  async function handleSave() {
    if (!id) return;
    try {
      const updated = await updateTool(id, {
        display_name: editDisplayName,
        description: editDescription,
        is_sandbox_safe: editIsSandboxSafe,
        parameters_schema: JSON.parse(editParametersSchema),
      });
      setTool(updated);
      setEditing(false);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleDelete() {
    if (!id || !tool) return;
    if (!confirm(`Delete tool "${tool.display_name}"?`)) return;
    try {
      await deleteTool(id);
      navigate("/tools");
    } catch (e) {
      setError(String(e));
    }
  }

  if (loading) return <div className="loading">Loading...</div>;
  if (error && !tool) return <div className="error">{error}</div>;
  if (!tool) return <div className="error">Tool not found</div>;

  return (
    <>
      <div className="page-header">
        <h1>{editing ? "Edit Tool" : tool.display_name}</h1>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {!editing && (
            <>
              <button className="btn" onClick={startEditing}>
                Edit
              </button>
              {!tool.is_builtin && (
                <button className="btn btn-danger" onClick={handleDelete}>
                  Delete
                </button>
              )}
            </>
          )}
          <Link to="/tools" className="btn">
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
            <label className="form-label">Display Name</label>
            <input
              className="form-input"
              value={editDisplayName}
              onChange={(e) => setEditDisplayName(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              rows={3}
            />
          </div>

          {!tool.is_builtin && (
            <div className="form-group">
              <label className="form-checkbox-label">
                <input
                  type="checkbox"
                  checked={editIsSandboxSafe}
                  onChange={(e) => setEditIsSandboxSafe(e.target.checked)}
                />
                Sandbox safe
              </label>
              <span className="form-hint">
                Sandbox-safe tools operate entirely inside the agent's isolated
                environment.
              </span>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Parameters Schema (JSON)</label>
            <textarea
              className="form-textarea"
              value={editParametersSchema}
              onChange={(e) => setEditParametersSchema(e.target.value)}
              rows={6}
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
            <h2>Details</h2>
            <div className="detail-grid">
              <span className="detail-label">Name</span>
              <span className="detail-value">
                <code>{tool.name}</code>
              </span>
              <span className="detail-label">Type</span>
              <span className="detail-value">
                {tool.is_builtin ? (
                  <span className="status status-inactive">built-in</span>
                ) : (
                  <span className="status status-active">custom</span>
                )}
              </span>
              <span className="detail-label">Sandbox Safe</span>
              <span className="detail-value">
                <span
                  className={`status ${tool.is_sandbox_safe ? "status-active" : "status-error"}`}
                >
                  {tool.is_sandbox_safe ? "yes" : "no"}
                </span>
              </span>
              <span className="detail-label">Enabled</span>
              <span className="detail-value">
                <span
                  className={`status ${tool.is_enabled ? "status-active" : "status-inactive"}`}
                >
                  {tool.is_enabled ? "yes" : "no"}
                </span>
              </span>
              <span className="detail-label">Created</span>
              <span className="detail-value">
                {new Date(tool.created_at).toLocaleString()}
              </span>
              <span className="detail-label">Updated</span>
              <span className="detail-value">
                {new Date(tool.updated_at).toLocaleString()}
              </span>
            </div>
          </div>

          {tool.description && (
            <div className="detail-section">
              <h2>Description</h2>
              <p>{tool.description}</p>
            </div>
          )}

          <div className="detail-section">
            <h2>Parameters Schema</h2>
            <pre className="detail-code">
              {JSON.stringify(tool.parameters_schema, null, 2)}
            </pre>
          </div>
        </>
      )}
    </>
  );
}
