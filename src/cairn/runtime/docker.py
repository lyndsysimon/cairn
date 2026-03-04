"""Docker runtime provider for executing agents in isolated containers."""

import asyncio
import json
import logging
from uuid import uuid4

from cairn.config import settings
from cairn.models.agent import AgentDefinition
from cairn.models.credential import CredentialValue
from cairn.models.run import AgentRun, RunStatus

logger = logging.getLogger(__name__)

# Label applied to all containers managed by Cairn.
CAIRN_LABEL = "cairn.managed=true"


class DockerRuntimeProvider:
    """Runs agents inside Docker containers.

    Lifecycle:
      1. start_agent  – creates and starts a container
      2. get_run_status / get_run_output – polls the container
      3. cancel_run   – stops a running container
      4. cleanup      – removes the container
    """

    @property
    def name(self) -> str:
        return "docker"

    # ------------------------------------------------------------------
    # Public interface (matches RuntimeProvider protocol)
    # ------------------------------------------------------------------

    async def start_agent(
        self,
        agent: AgentDefinition,
        input_data: dict,
        credentials: list[CredentialValue],
    ) -> AgentRun:
        container_name = f"cairn-{agent.id}-{uuid4().hex[:8]}"
        image = agent.runtime.image or "python:3.13-slim"
        timeout = agent.runtime.timeout_seconds or settings.default_timeout_seconds
        memory = agent.runtime.memory_limit_mb

        env_flags = self._build_env_flags(agent, input_data, credentials)
        cmd = self._build_run_command(
            container_name=container_name,
            image=image,
            env_flags=env_flags,
            memory_mb=memory,
            timeout=timeout,
        )

        logger.info("Starting container %s (image=%s)", container_name, image)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            error = stderr.decode().strip() if stderr else "Failed to start container"
            logger.error("Container start failed: %s", error)
            return AgentRun(
                agent_id=agent.id,
                status=RunStatus.FAILED,
                input_data=input_data,
                error_message=error,
            )

        return AgentRun(
            agent_id=agent.id,
            status=RunStatus.RUNNING,
            input_data=input_data,
            # Store container name so we can inspect / stop / remove later.
            output_data={"_container": container_name},
        )

    async def get_run_status(self, run: AgentRun) -> RunStatus:
        container = self._container_name(run)
        if container is None:
            return RunStatus.FAILED

        state = await self._inspect_state(container)
        if state is None:
            return RunStatus.FAILED

        if state.get("Running"):
            return RunStatus.RUNNING

        exit_code = state.get("ExitCode", -1)
        return RunStatus.COMPLETED if exit_code == 0 else RunStatus.FAILED

    async def get_run_output(self, run: AgentRun) -> dict | None:
        container = self._container_name(run)
        if container is None:
            return None

        proc = await asyncio.create_subprocess_exec(
            "docker",
            "logs",
            container,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None

        raw = stdout.decode().strip()
        # Try to parse the last line as JSON (agent output convention).
        last_line = raw.rsplit("\n", 1)[-1] if raw else ""
        try:
            return json.loads(last_line)
        except (json.JSONDecodeError, ValueError):
            return {"raw_output": raw}

    async def cancel_run(self, run: AgentRun) -> None:
        container = self._container_name(run)
        if container is None:
            return
        logger.info("Stopping container %s", container)
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "stop",
            "-t",
            "10",
            container,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    async def cleanup(self, run: AgentRun) -> None:
        container = self._container_name(run)
        if container is None:
            return
        logger.info("Removing container %s", container)
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "rm",
            "-f",
            container,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _container_name(run: AgentRun) -> str | None:
        if run.output_data and "_container" in run.output_data:
            return run.output_data["_container"]
        return None

    @staticmethod
    def _build_env_flags(
        agent: AgentDefinition,
        input_data: dict,
        credentials: list[CredentialValue],
    ) -> list[str]:
        flags: list[str] = []

        # Inject input data as CAIRN_INPUT.
        flags += ["-e", f"CAIRN_INPUT={json.dumps(input_data)}"]

        # Inject agent-level static env vars.
        for key, value in agent.runtime.environment.items():
            flags += ["-e", f"{key}={value}"]

        # Map each credential to the env var name declared in the agent def.
        cred_lookup = {c.credential_id: c.value for c in credentials}
        for ref in agent.credentials:
            value = cred_lookup.get(ref.credential_id, "")
            flags += ["-e", f"{ref.env_var_name}={value}"]

        return flags

    @staticmethod
    def _build_run_command(
        *,
        container_name: str,
        image: str,
        env_flags: list[str],
        memory_mb: int,
        timeout: int,
    ) -> list[str]:
        return [
            "docker",
            "run",
            "-d",  # detached
            "--name",
            container_name,
            "--label",
            CAIRN_LABEL,
            "--network",
            "none",  # no network by default
            "--read-only",  # read-only root fs
            "--tmpfs",
            "/tmp:rw,noexec,size=64m",
            f"--memory={memory_mb}m",
            f"--stop-timeout={timeout}",
            *env_flags,
            image,
        ]

    @staticmethod
    async def _inspect_state(container: str) -> dict | None:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "inspect",
            "--format",
            "{{json .State}}",
            container,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        try:
            return json.loads(stdout.decode().strip())
        except (json.JSONDecodeError, ValueError):
            return None
