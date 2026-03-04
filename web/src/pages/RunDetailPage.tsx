import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getRun } from "../api/client";
import type { AgentRun } from "../api/types";

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

function formatDuration(run: AgentRun): string {
  if (!run.started_at) return "—";
  const start = new Date(run.started_at).getTime();
  const end = run.completed_at
    ? new Date(run.completed_at).getTime()
    : Date.now();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    getRun(runId)
      .then(setRun)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!run) return <div className="error">Run not found</div>;

  return (
    <>
      <div className="page-header">
        <h1>Run Details</h1>
        <Link to={`/agents/${run.agent_id}`} className="btn">
          Back to Agent
        </Link>
      </div>

      <div className="detail-section">
        <h2>Overview</h2>
        <div className="detail-grid">
          <span className="detail-label">Status</span>
          <span className="detail-value">
            <RunStatusBadge status={run.status} />
          </span>
          <span className="detail-label">Created</span>
          <span className="detail-value">
            {new Date(run.created_at).toLocaleString()}
          </span>
          {run.started_at && (
            <>
              <span className="detail-label">Started</span>
              <span className="detail-value">
                {new Date(run.started_at).toLocaleString()}
              </span>
            </>
          )}
          {run.completed_at && (
            <>
              <span className="detail-label">Completed</span>
              <span className="detail-value">
                {new Date(run.completed_at).toLocaleString()}
              </span>
            </>
          )}
          <span className="detail-label">Duration</span>
          <span className="detail-value">{formatDuration(run)}</span>
        </div>
      </div>

      {run.input_data && (
        <div className="detail-section">
          <h2>Input</h2>
          <pre className="detail-code">
            {JSON.stringify(run.input_data, null, 2)}
          </pre>
        </div>
      )}

      {run.output_data && (
        <div className="detail-section">
          <h2>Output</h2>
          <pre className="detail-code">
            {JSON.stringify(run.output_data, null, 2)}
          </pre>
        </div>
      )}

      {run.error_message && (
        <div className="detail-section">
          <h2>Error</h2>
          <pre className="detail-code detail-code-error">
            {run.error_message}
          </pre>
        </div>
      )}
    </>
  );
}
