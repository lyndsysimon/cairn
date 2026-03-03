# Agent Orchestration Platform — Project Definition

**Version 0.1 — March 2026**
**Status: Draft**

---

## 1. Overview

This document defines an agent orchestration platform: a system in which autonomous AI agents execute tasks in isolated environments, coordinated by a central orchestration agent. The platform enables users to define, manage, trigger, and monitor agents that perform work ranging from simple one-shot tasks to complex, multi-step workflows involving sub-agent delegation.

The system is designed around the principles of strict isolation, minimal privilege, explicit context boundaries, and defense-in-depth security.

---

## 2. Core Concepts

### 2.1 Agents

An agent is a discrete unit of work that runs in response to a trigger. Each agent is defined by the following properties:

- **Model and Provider**: The LLM model and provider to use for inference (e.g., Claude Sonnet via Anthropic).
- **Context**: Explicitly defined input context. Agents do not share context with any other part of the system unless the user has explicitly configured it at agent creation time.
- **Input Schema**: A JSON schema defining the expected input to the agent.
- **Output Schema**: A JSON schema defining the structure of the agent's response. All agent output is returned as JSON conforming to this schema.
- **Trigger Type**: How the agent is invoked (see Trigger Types below).
- **Runtime Provider**: The isolated execution environment in which the agent runs (see Runtime Providers).
- **Credentials**: A whitelist of credential references the agent is permitted to access, drawn from a configured Credential Store.

### 2.2 Trigger Types

Agents can be invoked through the following trigger mechanisms:

| Trigger Type | Description |
|---|---|
| Manual | Invoked directly by the user or by the orchestration agent via a tool call. |
| Scheduled (Cron) | Runs on a user-defined schedule (e.g., every 15 minutes, daily at 08:00). |
| Event / Webhook | Triggered by an inbound HTTP event or webhook. |
| Agent-to-Agent | Triggered by another agent as part of a workflow or delegation chain. |

### 2.3 The Orchestration Agent

The orchestration agent (also referred to as the "main agent") is the user's primary point of interaction. It serves as the central coordinator for all other agents in the system.

Key characteristics:

- **Persona**: The orchestration agent has a configurable personality and conversational style. It is the "face" of the system.
- **Credential Access**: Has access to all credentials by default, but operates under strict constraints — it cannot directly act on the outside world.
- **No Direct External Access**: The orchestration agent has no internet access, no filesystem access beyond a temporary directory, and no ability to execute code outside its sandbox. All external actions are performed by delegating to purpose-built agents via tool calls.
- **Multi-Channel**: Users interact with the orchestration agent over multiple channels: a web UI, CLI, Signal, and any additional channels configured in the future.

---

## 3. Architecture

### 3.1 Runtime Providers

Each agent runs in an isolated execution environment provisioned by a runtime provider. Runtime providers implement a consistent interface, allowing the platform to abstract away the underlying technology. The following providers are supported, in order of preference:

| Priority | Provider | Notes |
|---|---|---|
| 1 | Apple Container | macOS-native lightweight containers (preferred on Apple Silicon). |
| 2 | Podman | Rootless, daemonless container engine. Cross-platform. |
| 3 | Docker / Docker Compose | Widely available fallback. |
| 4 | AWS Lambda | For serverless / cloud-hosted agent execution. |

Users may also provide custom runtime providers for platforms not listed above. Custom providers must implement the same interface as built-in providers.

### 3.2 Credential Stores

Credentials (API keys, OAuth tokens, service accounts, etc.) are managed through a pluggable Credential Store abstraction. Supported stores:

- **Bitwarden**: Integrates with an existing Bitwarden vault for credential retrieval.
- **PostgreSQL (Encrypted)**: Credentials stored in the application database, salted and encrypted using an application-level secret.

As with runtime providers, custom credential store providers will be supported via a consistent interface.

### 3.3 Data Layer

The platform uses PostgreSQL as its primary data store for agent definitions, run history, scheduling metadata, and system configuration. The orchestration agent also has access to a temporary directory for handling user-uploaded files and ephemeral data.

If a compelling reason arises to introduce an additional data store (e.g., a message queue or cache), this should be discussed and approved before implementation.

### 3.4 Agent Isolation Model

Agent isolation is a foundational architectural principle:

- Each agent runs in its own execution environment, provisioned by a runtime provider.
- Agents receive only the credentials explicitly whitelisted for them — never the full credential set.
- Agents receive only the context explicitly defined in their configuration — no implicit context sharing.
- Agents have no access to the host filesystem, the database, or other agents' environments.
- All communication between agents is mediated through the platform's defined interfaces (tool calls, JSON input/output).

---

## 4. Security

Security is a first-class concern throughout the platform. The following threat models and mitigations are integral to the design.

### 4.1 Threat Model

#### 4.1.1 Credential and Context Leakage

Credentials and sensitive context must never be exposed through API endpoints, logs, agent outputs, or error messages. Agents only receive the credentials and context explicitly configured for them.

#### 4.1.2 Execution Environment Boundary Violations

Agents must never gain access to credentials, files, or execution capabilities beyond what has been explicitly provisioned. The runtime provider is responsible for enforcing this boundary.

#### 4.1.3 Supply-Chain Attacks

Modifications to base execution runtimes (container images, Lambda configurations, etc.) must not occur without explicit user approval. Any change to a runtime's base image or dependencies should require user confirmation.

#### 4.1.4 Prompt Injection

Any time an agent retrieves content from the web or processes external data, there is a risk of prompt injection — malicious instructions embedded in the content that attempt to extract secrets or alter agent behavior. This is addressed by the Security Middleware Layer (see below).

### 4.2 Security Middleware Layer

A dedicated security middleware layer sits between agents and the outside world. This layer performs the following inspections:

- **Outbound Prompt Inspection**: Before a prompt is sent to an LLM, the middleware scans it for any credentials or secrets that should not be present in the prompt context.
- **Inbound Response Inspection**: When an agent processes content retrieved from external sources (web pages, APIs, webhooks), the middleware inspects that content for embedded instructions or prompt injection attempts before it enters the agent's context.

This layer is especially critical for agents that perform web research, content retrieval, or process untrusted input.

---

## 5. User Interaction

### 5.1 Channels

Users interact with the orchestration agent through multiple channels:

- **Web UI**: A minimal, professional web interface for chat, agent management, and observability. Built with TypeScript and React.
- **CLI**: A command-line interface for direct interaction with the orchestration agent.
- **Signal**: Messaging integration for mobile-friendly conversational access.
- **Extensible**: Additional channels can be configured in the future.

### 5.2 Agent Management

The system must make it quick and easy for users to:

- View all agents they have created, along with their current status and configuration.
- Create new agents with a streamlined workflow.
- Edit agent definitions (model, provider, context, schemas, triggers, credentials).
- View run history and logs for each agent.
- Manually trigger agents.

### 5.3 Observability

A simple web UI provides monitoring capabilities including agent run status, logs, and sub-agent activity. Observability features will be expanded in future iterations.

---

## 6. Example Use Cases

### 6.1 Real-Time News Monitoring

A user creates a monitoring agent that watches X (Twitter), Facebook, major news outlets, and specific forums for reports of military activity. When at least three independent claims of military strikes are detected, the agent immediately notifies the user. This demonstrates scheduled/event-driven triggers, web content retrieval, and the importance of prompt injection defenses on retrieved content.

### 6.2 Application Development Workflow

A user describes an idea for a software product to the orchestration agent, which files it as a project idea. When the user decides to proceed, a "product manager" agent works with the user to flesh out capabilities and features, then spins up sub-agents to implement the project. Work may begin before the project is fully defined, as long as sufficient context has been provided. The entire workflow is conversational — the user interacts via chat or the web UI, and the product manager agent works in the background while remaining available for questions.

### 6.3 One-Shot Task: YouTube Audio Extraction

The user sends a URL to the orchestration agent and asks for the audio to be extracted as MP3. The orchestration agent delegates to a "YouTube Audio Extraction" agent, providing only the URL. That agent uses yt-dlp in its isolated environment to download and convert the audio, returning the file as output. The orchestration agent persists the file and replies to the user. This demonstrates single-shot delegation with minimal context passing.

### 6.4 Self-Improvement

The user asks the orchestration agent to add a new capability (e.g., "I'd like you to be able to post for me on Facebook"). The orchestration agent delegates to a product manager agent to plan the implementation. The plan is saved as a Markdown file and presented to the user for review. Upon approval, the orchestration agent triggers a project manager agent to implement, test, and integrate the new capability. Once complete, the orchestration agent informs the user. This demonstrates the self-improvement loop: the system can extend its own capabilities through its own agent framework.

---

## 7. Tech Stack

| Component | Technology |
|---|---|
| Core Platform / Backend | Python |
| Web UI | TypeScript, React |
| Component Development | React Storybook (or equivalent) |
| Database | PostgreSQL |
| Agent Runtimes | Apple Container, Podman, Docker, AWS Lambda |
| Credential Stores | Bitwarden, PostgreSQL (encrypted) |

Code should be kept as clean and minimal as possible. The web UI should be minimal but professional, designed to support easy theming in the future.

---

## 8. Platform Support

The system must run on macOS, Linux, and Windows.

---

## 9. Open Questions

The following areas require further definition as the project progresses:

- Detailed authentication and authorization model for the web UI and API.
- Rate limiting and cost controls for LLM API usage.
- Agent versioning and rollback strategy.
- Detailed observability and logging architecture (deferred to a future iteration).
- Specific protocols for the self-improvement workflow (safety gates, testing requirements, rollback).
- Message queuing or event bus architecture for agent-to-agent communication at scale.
- Backup and disaster recovery strategy for the PostgreSQL data layer.
