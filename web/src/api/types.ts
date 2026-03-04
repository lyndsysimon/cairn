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
