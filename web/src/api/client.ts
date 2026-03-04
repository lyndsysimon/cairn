import type {
  Agent,
  AgentListResponse,
  AgentRun,
  CreateAgentRequest,
  CreateCredentialRequest,
  CreateProviderRequest,
  CreateRunRequest,
  Credential,
  CredentialListResponse,
  ModelProvider,
  ProviderListResponse,
  RunListResponse,
  UpdateAgentRequest,
  UpdateCredentialRequest,
  UpdateProviderRequest,
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

// --- Model Providers ---

export function listProviders(
  enabledOnly?: boolean,
): Promise<ProviderListResponse> {
  const params = enabledOnly ? "?enabled_only=true" : "";
  return request(`/providers${params}`);
}

export function getProvider(id: string): Promise<ModelProvider> {
  return request(`/providers/${id}`);
}

export function createProvider(
  data: CreateProviderRequest,
): Promise<ModelProvider> {
  return request("/providers", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateProvider(
  id: string,
  data: UpdateProviderRequest,
): Promise<ModelProvider> {
  return request(`/providers/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteProvider(id: string): Promise<void> {
  return request(`/providers/${id}`, { method: "DELETE" });
}

// --- Credentials ---

export function listCredentials(
  storeName?: string,
): Promise<CredentialListResponse> {
  const params = storeName ? `?store_name=${encodeURIComponent(storeName)}` : "";
  return request(`/credentials${params}`);
}

export function getCredential(id: string): Promise<Credential> {
  return request(`/credentials/${id}`);
}

export function createCredential(
  data: CreateCredentialRequest,
): Promise<Credential> {
  return request("/credentials", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateCredential(
  id: string,
  data: UpdateCredentialRequest,
): Promise<Credential> {
  return request(`/credentials/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteCredential(id: string): Promise<void> {
  return request(`/credentials/${id}`, { method: "DELETE" });
}

// --- Agent Runs ---

export function listRuns(agentId: string): Promise<RunListResponse> {
  return request(`/agents/${agentId}/runs`);
}

export function getRun(runId: string): Promise<AgentRun> {
  return request(`/runs/${runId}`);
}

export function createRun(
  agentId: string,
  data: CreateRunRequest,
): Promise<AgentRun> {
  return request(`/agents/${agentId}/runs`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
