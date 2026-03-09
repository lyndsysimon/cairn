import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listTools, updateTool, deleteTool } from "../api/client";
import type { Tool } from "../api/types";

export function ToolListPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTools();
  }, []);

  function loadTools() {
    setLoading(true);
    listTools()
      .then((data) => setTools(data.tools))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }

  async function handleToggleEnabled(tool: Tool) {
    try {
      const updated = await updateTool(tool.id, {
        is_enabled: !tool.is_enabled,
      });
      setTools((prev) => prev.map((t) => (t.id === tool.id ? updated : t)));
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleDelete(tool: Tool) {
    if (!confirm(`Delete tool "${tool.display_name}"?`)) return;
    try {
      await deleteTool(tool.id);
      setTools((prev) => prev.filter((t) => t.id !== tool.id));
    } catch (e) {
      setError(String(e));
    }
  }

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <>
      <div className="page-header">
        <h1>Tools</h1>
        <Link to="/tools/new" className="btn btn-primary">
          Add Tool
        </Link>
      </div>

      {tools.length === 0 ? (
        <div className="empty-state">
          <p>No tools configured yet.</p>
          <Link to="/tools/new" className="btn btn-primary">
            Add Tool
          </Link>
        </div>
      ) : (
        <table className="agent-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>Sandbox Safe</th>
              <th>Enabled</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tools.map((tool) => (
              <tr key={tool.id}>
                <td>
                  <Link
                    to={`/tools/${tool.id}`}
                    className="agent-name-link"
                  >
                    {tool.display_name}
                  </Link>
                  {tool.is_builtin && (
                    <span
                      className="status status-inactive"
                      style={{ marginLeft: "0.5rem" }}
                    >
                      built-in
                    </span>
                  )}
                </td>
                <td>{tool.description || "—"}</td>
                <td>
                  <span
                    className={`status ${tool.is_sandbox_safe ? "status-active" : "status-error"}`}
                  >
                    {tool.is_sandbox_safe ? "yes" : "no"}
                  </span>
                </td>
                <td>
                  <button
                    className={`btn btn-sm ${tool.is_enabled ? "btn-primary" : ""}`}
                    onClick={() => handleToggleEnabled(tool)}
                  >
                    {tool.is_enabled ? "Enabled" : "Disabled"}
                  </button>
                </td>
                <td>
                  {!tool.is_builtin && (
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDelete(tool)}
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
