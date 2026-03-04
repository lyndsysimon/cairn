from typing import Protocol

from cairn.models.agent import AgentDefinition
from cairn.models.credential import CredentialValue
from cairn.models.run import AgentRun, RunStatus


class RuntimeProvider(Protocol):
    """Interface for agent execution environments.

    Each runtime provider manages the lifecycle of agent execution:
    provisioning an isolated environment, injecting credentials,
    running the agent, and collecting output.
    """

    @property
    def name(self) -> str: ...

    async def start_agent(
        self,
        agent: AgentDefinition,
        input_data: dict,
        credentials: list[CredentialValue],
    ) -> AgentRun: ...

    async def get_run_status(self, run: AgentRun) -> RunStatus: ...

    async def get_run_output(self, run: AgentRun) -> dict | None: ...

    async def cancel_run(self, run: AgentRun) -> None: ...

    async def cleanup(self, run: AgentRun) -> None: ...
