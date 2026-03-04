import type {
  Agent,
  AgentListResponse,
  CreateAgentRequest,
  UpdateAgentRequest,
} from "./types";

const BASE = "/api";

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function listAgents(): Promise<AgentListResponse> {
  return request("/agents");
}

export function getAgent(id: string): Promise<Agent> {
  return request(`/agents/${id}`);
}

export function createAgent(data: CreateAgentRequest): Promise<Agent> {
  return request("/agents", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateAgent(
  id: string,
  data: UpdateAgentRequest,
): Promise<Agent> {
  return request(`/agents/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteAgent(id: string): Promise<void> {
  return request(`/agents/${id}`, { method: "DELETE" });
}
