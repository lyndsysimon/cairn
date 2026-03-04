import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  getAgent,
  updateAgent,
  deleteAgent,
  listRuns,
  createRun,
} from "../api/client";
import type { Agent, AgentRun, AgentStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

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
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editSystemPrompt, setEditSystemPrompt] = useState("");
  const [editStatus, setEditStatus] = useState<AgentStatus>("active");

  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [showRunInput, setShowRunInput] = useState(false);
  const [runInput, setRunInput] = useState("{}");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getAgent(id)
      .then((a) => {
        setAgent(a);
        setEditName(a.name);
        setEditDescription(a.description);
        setEditSystemPrompt(a.system_prompt);
        setEditStatus(a.status);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));

    loadRuns(id);
  }, [id]);

  function loadRuns(agentId: string) {
    setRunsLoading(true);
    listRuns(agentId)
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
      loadRuns(id);
    } catch (e) {
      setError(String(e));
    } finally {
      setTriggering(false);
    }
  }

  async function handleSave() {
    if (!id) return;
    try {
      const updated = await updateAgent(id, {
        name: editName,
        description: editDescription,
        system_prompt: editSystemPrompt,
        status: editStatus,
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
              <button className="btn" onClick={() => setEditing(true)}>
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
            <label className="form-label">System Prompt</label>
            <textarea
              className="form-textarea"
              value={editSystemPrompt}
              onChange={(e) => setEditSystemPrompt(e.target.value)}
              rows={4}
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
                <StatusBadge status={agent.status} />
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
              {"path" in agent.trigger && (
                <>
                  <span className="detail-label">Path</span>
                  <span className="detail-value">
                    <code>{agent.trigger.path}</code>
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
          </div>

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
                No runs yet.
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
                      const start = new Date(run.started_at).getTime();
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
                          {new Date(run.created_at).toLocaleString()}
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
