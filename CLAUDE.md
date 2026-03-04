# Agent Orchestration Platform

A platform for defining, managing, and running autonomous AI agents in isolated execution environments, coordinated by a central orchestration agent. Users define agents with explicit I/O schemas, triggers, and credentials; the orchestration agent delegates all external work to purpose-built sub-agents.

## Project Definition

For full architecture, security model, threat model, use cases, and requirements, read `docs/project-definition.md`. Always consult this document before making architectural decisions or introducing new components.

## Tech Stack

- Backend: Python (keep dependencies minimal)
- Web UI: TypeScript, React
- Component development: React Storybook or equivalent
- Database: PostgreSQL (do not introduce additional data stores without confirmation)
- Agent runtimes: Apple Container, Podman, Docker, AWS Lambda (pluggable via a consistent interface)
- Credential stores: Bitwarden, PostgreSQL (encrypted) (also pluggable)

## Core Principles

- **Security is paramount.** Agents run in strict isolation. No credential leakage, no implicit context sharing, no uncontrolled external access. A security middleware layer inspects all prompts for secrets and all responses for prompt injection. See the Security section of the project definition for the full threat model.
- **Explicit over implicit.** Agents receive only the context, credentials, and environment explicitly configured for them. The orchestration agent has no direct internet or filesystem access beyond a temp directory — it acts on the world solely via tool calls to other agents.
- **Defined I/O.** Every agent has a JSON input schema and a JSON output schema defined at creation time.
- **Clean and minimal.** Keep code, dependencies, and UI as lean as possible. The UI should be professional, minimal, and designed for easy theming later.

## Key Architectural Concepts

- **Orchestration Agent**: The user's primary interface. Has a persona/personality. Has access to all credentials but cannot act externally — delegates everything. Reachable via web UI, CLI, and Signal.
- **Runtime Providers**: Pluggable isolated execution environments (Apple Container > Podman > Docker > AWS Lambda). Must implement a consistent interface. Users can provide custom providers.
- **Credential Stores**: Pluggable credential management (Bitwarden, encrypted PostgreSQL). Users can provide custom stores.
- **Security Middleware**: Sits between agents and the outside world. Inspects outbound prompts for secret leakage and inbound responses for prompt injection.
- **Triggers**: Manual, scheduled (cron), event/webhook, or agent-to-agent.

## Development Workflow

- **Always run `ruff format src/ tests/` and `ruff check src/ tests/` before committing and pushing.** CI will reject unformatted code.

## Platform Support

macOS, Linux, and Windows.
