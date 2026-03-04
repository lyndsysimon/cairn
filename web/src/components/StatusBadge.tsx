import type { AgentStatus } from "../api/types";

export function StatusBadge({ status }: { status: AgentStatus }) {
  return <span className={`status status-${status}`}>{status}</span>;
}
