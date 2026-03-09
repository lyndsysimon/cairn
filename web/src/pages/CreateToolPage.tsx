import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { createTool } from "../api/client";

export function CreateToolPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [isSandboxSafe, setIsSandboxSafe] = useState(true);
  const [parametersSchema, setParametersSchema] = useState('{"type": "object"}');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const tool = await createTool({
        name,
        display_name: displayName,
        description,
        is_sandbox_safe: isSandboxSafe,
        parameters_schema: JSON.parse(parametersSchema),
      });
      navigate(`/tools/${tool.id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Add Tool</h1>
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
            placeholder="web-search"
          />
          <span className="form-hint">
            A unique identifier for this tool (lowercase, hyphens)
          </span>
        </div>

        <div className="form-group">
          <label className="form-label">Display Name</label>
          <input
            className="form-input"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            maxLength={255}
            placeholder="Web Search"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Description</label>
          <textarea
            className="form-textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="What does this tool do?"
          />
        </div>

        <div className="form-group">
          <label className="form-checkbox-label">
            <input
              type="checkbox"
              checked={isSandboxSafe}
              onChange={(e) => setIsSandboxSafe(e.target.checked)}
            />
            Sandbox safe
          </label>
          <span className="form-hint">
            Sandbox-safe tools operate entirely inside the agent's isolated
            environment and can be called directly by any agent. Non-sandbox-safe
            tools access external resources and must be mediated for agents with
            secrets.
          </span>
        </div>

        <div className="form-group">
          <label className="form-label">Parameters Schema (JSON)</label>
          <textarea
            className="form-textarea"
            value={parametersSchema}
            onChange={(e) => setParametersSchema(e.target.value)}
            rows={4}
          />
          <span className="form-hint">
            JSON Schema for the tool's input parameters
          </span>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
          >
            {submitting ? "Saving..." : "Add Tool"}
          </button>
          <Link to="/tools" className="btn">
            Cancel
          </Link>
        </div>
      </form>
    </>
  );
}
