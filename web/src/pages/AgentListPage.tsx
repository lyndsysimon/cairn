import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAgents, deleteAgent } from "../api/client";
import type { Agent, AgentStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

const AGENT_STATUSES: AgentStatus[] = ["active", "inactive", "error"];

export function AgentListPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");

  async function load(status?: string) {
    try {
      setLoading(true);
      const data = await listAgents(status);
      setAgents(data.agents);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(statusFilter || undefined);
  }, [statusFilter]);

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete agent "${name}"?`)) return;
    try {
      await deleteAgent(id);
      setAgents((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Agents</h1>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <select
            className="form-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ width: "auto", minWidth: "140px" }}
          >
            <option value="">All statuses</option>
            {AGENT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <Link to="/agents/new" className="btn btn-primary">
            + New Agent
          </Link>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="loading">Loading agents...</div>
      ) : agents.length === 0 ? (
        <div className="empty-state">
          <p>No agents yet.</p>
          <Link to="/agents/new" className="btn btn-primary">
            Create your first agent
          </Link>
        </div>
      ) : (
        <table className="agent-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Model</th>
              <th>Trigger</th>
              <th>Runtime</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
              <tr key={agent.id}>
                <td>
                  <Link
                    to={`/agents/${agent.id}`}
                    className="agent-name-link"
                  >
                    {agent.name}
                  </Link>
                </td>
                <td>{agent.model_name}</td>
                <td>{agent.trigger.type}</td>
                <td>{agent.runtime.type}</td>
                <td>
                  <StatusBadge status={agent.status} />
                </td>
                <td>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDelete(agent.id, agent.name)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
