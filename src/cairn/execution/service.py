"""Agent execution service.

Coordinates the full lifecycle of an agent run:
  1. Resolve credentials
  2. Inspect outbound prompt/input via security middleware
  3. Provision and start the agent container via a runtime provider
  4. Poll for completion
  5. Collect and inspect output
  6. Persist final run state
"""

import asyncio
import logging

from psycopg import AsyncConnection

from cairn.credentials.base import CredentialStore
from cairn.db.repositories import run_repo
from cairn.models.agent import AgentDefinition
from cairn.models.credential import CredentialValue
from cairn.models.run import AgentRun, RunStatus
from cairn.runtime.base import RuntimeProvider
from cairn.security.base import SecurityPipeline

logger = logging.getLogger(__name__)

# How often (seconds) we poll a running container for completion.
_POLL_INTERVAL = 2.0


class ExecutionService:
    """Drives a single agent run from start to finish."""

    def __init__(
        self,
        runtime: RuntimeProvider,
        security: SecurityPipeline,
        credential_store: CredentialStore | None = None,
    ) -> None:
        self._runtime = runtime
        self._security = security
        self._credential_store = credential_store

    async def execute(
        self,
        agent: AgentDefinition,
        run: AgentRun,
        conn: AsyncConnection,
    ) -> AgentRun:
        """Run the full execution lifecycle. Returns the final AgentRun."""
        try:
            # 0. Build per-agent security pipeline
            pipeline = self._security.for_agent(agent)

            # 1. Resolve credentials
            credentials = await self._resolve_credentials(agent)

            # 2. Security: inspect outbound input for leaked secrets
            credential_values = [c.value for c in credentials]
            input_json = run.input_data or {}
            sanitized_input = await pipeline.inspect_outbound(
                str(input_json), credential_values
            )
            # If the middleware rewrote the input, log it but keep going.
            if sanitized_input != str(input_json):
                logger.warning("Security middleware modified outbound input for run %s", run.id)

            # 3. Mark run as RUNNING
            run = await run_repo.update_status(conn, run.id, RunStatus.RUNNING)
            await conn.commit()

            # 4. Start the agent in the runtime
            runtime_run = await self._runtime.start_agent(agent, input_json, credentials)

            if runtime_run.status == RunStatus.FAILED:
                run = await run_repo.update_status(
                    conn, run.id, RunStatus.FAILED,
                    error_message=runtime_run.error_message or "Runtime failed to start agent",
                )
                await conn.commit()
                return run

            # Persist the container metadata (e.g. container name) on the run.
            container_meta = runtime_run.output_data
            if container_meta:
                run = await run_repo.update_status(
                    conn, run.id, RunStatus.RUNNING,
                    output_data=container_meta,
                )
                await conn.commit()
                # Refresh run object with container metadata for polling.
                run = run.model_copy(update={"output_data": container_meta})

            # 5. Poll until the container finishes or times out
            timeout = agent.runtime.timeout_seconds
            run = await self._poll_until_done(run, timeout)

            # 6. Collect output
            output = await self._runtime.get_run_output(run)

            # 7. Security: inspect inbound output for prompt injection
            if output:
                sanitized_output, warnings = await pipeline.inspect_inbound(
                    str(output)
                )
                if warnings:
                    logger.warning(
                        "Security warnings on run %s output: %s", run.id, warnings
                    )

            # 8. Persist final state
            final_status = await self._runtime.get_run_status(run)
            if final_status == RunStatus.COMPLETED:
                run = await run_repo.update_status(
                    conn, run.id, RunStatus.COMPLETED, output_data=output
                )
            else:
                run = await run_repo.update_status(
                    conn, run.id, RunStatus.FAILED,
                    error_message="Agent exited with non-zero status",
                    output_data=output,
                )
            await conn.commit()

        except asyncio.CancelledError:
            # Propagate cancellation but mark the run.
            await self._runtime.cancel_run(run)
            run = await run_repo.update_status(
                conn, run.id, RunStatus.CANCELLED,
            )
            await conn.commit()
            raise

        except Exception as exc:
            logger.exception("Execution failed for run %s", run.id)
            run = await run_repo.update_status(
                conn, run.id, RunStatus.FAILED,
                error_message=str(exc),
            )
            await conn.commit()

        finally:
            # Always clean up the container.
            try:
                await self._runtime.cleanup(run)
            except Exception:
                logger.exception("Cleanup failed for run %s", run.id)

        return run

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _resolve_credentials(
        self, agent: AgentDefinition
    ) -> list[CredentialValue]:
        if not agent.credentials or self._credential_store is None:
            return []
        results: list[CredentialValue] = []
        for ref in agent.credentials:
            value = await self._credential_store.get_credential(ref)
            results.append(value)
        return results

    async def _poll_until_done(
        self, run: AgentRun, timeout: int
    ) -> AgentRun:
        elapsed = 0.0
        while elapsed < timeout:
            status = await self._runtime.get_run_status(run)
            if status != RunStatus.RUNNING:
                return run
            await asyncio.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL

        # Timed out — cancel the container.
        logger.warning("Run %s timed out after %ss, cancelling", run.id, timeout)
        await self._runtime.cancel_run(run)
        return run
