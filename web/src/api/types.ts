export type TriggerType = "manual" | "scheduled" | "webhook" | "agent_to_agent";

export type ManualTrigger = { type: "manual" };
export type ScheduledTrigger = {
  type: "scheduled";
  cron_expression: string;
  timezone: string;
};
export type WebhookTrigger = { type: "webhook"; path: string };
export type AgentToAgentTrigger = {
  type: "agent_to_agent";
  source_agent_ids: string[];
};

export type TriggerConfig =
  | ManualTrigger
  | ScheduledTrigger
  | WebhookTrigger
  | AgentToAgentTrigger;

export type RuntimeType =
  | "apple_container"
  | "podman"
  | "docker"
  | "aws_lambda";

export interface RuntimeConfig {
  type: RuntimeType;
  image: string | null;
  timeout_seconds: number;
  memory_limit_mb: number;
  environment: Record<string, string>;
}

export interface CredentialReference {
  store_name: string;
  credential_id: string;
  env_var_name: string;
}

export type AgentStatus = "active" | "inactive" | "error";

export interface Agent {
  id: string;
  name: string;
  description: string;
  model_provider: string;
  model_name: string;
  system_prompt: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  trigger: TriggerConfig;
  runtime: RuntimeConfig;
  credentials: CredentialReference[];
  status: AgentStatus;
  created_at: string;
  updated_at: string;
}

export interface AgentListResponse {
  agents: Agent[];
  total: number;
}

export interface CreateAgentRequest {
  name: string;
  description?: string;
  model_provider: string;
  model_name: string;
  system_prompt?: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  trigger: TriggerConfig;
  runtime: Partial<RuntimeConfig> & { type: RuntimeType };
  credentials?: CredentialReference[];
}

export interface UpdateAgentRequest {
  name?: string;
  description?: string;
  model_provider?: string;
  model_name?: string;
  system_prompt?: string;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  trigger?: TriggerConfig;
  runtime?: Partial<RuntimeConfig> & { type: RuntimeType };
  credentials?: CredentialReference[];
  status?: AgentStatus;
}

// --- Model Provider types ---

export interface ModelConfig {
  model_id: string;
  display_name: string;
  is_enabled: boolean;
}

export interface ModelProvider {
  id: string;
  name: string;
  provider_type: string;
  api_base_url: string | null;
  api_key_credential_id: string | null;
  models: ModelConfig[];
  is_enabled: boolean;
  supports_model_discovery: boolean;
  created_at: string;
  updated_at: string;
}

export interface DiscoverModelsRequest {
  provider_type: string;
  api_base_url?: string | null;
  api_key_credential_id?: string | null;
}

export interface DiscoverModelsResponse {
  models: ModelConfig[];
}

export interface ProviderListResponse {
  providers: ModelProvider[];
  total: number;
}

export interface CreateProviderRequest {
  name: string;
  provider_type: string;
  api_base_url?: string | null;
  api_key_credential_id?: string | null;
  models?: ModelConfig[];
  is_enabled?: boolean;
}

export interface UpdateProviderRequest {
  name?: string;
  provider_type?: string;
  api_base_url?: string | null;
  api_key_credential_id?: string | null;
  models?: ModelConfig[];
  is_enabled?: boolean;
}

// --- Credential types ---

export interface Credential {
  id: string;
  credential_id: string;
  store_name: string;
  created_at: string;
  updated_at: string;
}

export interface CredentialListResponse {
  credentials: Credential[];
  total: number;
}

export interface CreateCredentialRequest {
  credential_id: string;
  store_name?: string;
  value: string;
}

export interface UpdateCredentialRequest {
  value: string;
}

// --- Agent Run types ---

export type RunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface AgentRun {
  id: string;
  agent_id: string;
  status: RunStatus;
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface RunListResponse {
  runs: AgentRun[];
  total: number;
}

export interface CreateRunRequest {
  input_data?: Record<string, unknown> | null;
}
