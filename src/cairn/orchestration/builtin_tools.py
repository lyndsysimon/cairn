"""Built-in tool executors for the orchestration agent.

Provides execution logic for built-in tools (e.g. bash) that run directly
in the server process rather than being delegated to sub-agents.
"""

import asyncio
import logging
from typing import Protocol

logger = logging.getLogger(__name__)

_BASH_TIMEOUT = 120


class BuiltinToolExecutor(Protocol):
    """Interface for executing a built-in tool."""

    async def execute(self, input_data: dict) -> dict:
        """Execute the tool and return the result dict."""
        ...


class BashToolExecutor:
    """Executes bash commands via subprocess."""

    def __init__(self, timeout: int = _BASH_TIMEOUT) -> None:
        self._timeout = timeout

    async def execute(self, input_data: dict) -> dict:
        command = input_data.get("command")
        if not command:
            return {"error": "No 'command' provided"}

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._timeout,
            )

            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }

        except TimeoutError:
            proc.kill()
            return {"error": f"Command timed out after {self._timeout}s"}
        except Exception as exc:
            logger.exception("Bash tool execution failed")
            return {"error": str(exc)}


# Registry of built-in tool executors, keyed by tool name (matching the DB name).
BUILTIN_EXECUTORS: dict[str, BuiltinToolExecutor] = {
    "bash": BashToolExecutor(),
}
