"""Cron scheduler for firing scheduled agent runs.

Periodically queries the database for active agents with scheduled triggers,
evaluates their cron expressions, and creates + executes runs for agents that
are due.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from croniter import croniter
from psycopg_pool import AsyncConnectionPool

from cairn.db.repositories import agent_repo, run_repo, schedule_repo
from cairn.execution.service import ExecutionService
from cairn.models.agent import AgentStatus
from cairn.models.run import AgentRun
from cairn.models.trigger import ScheduledTrigger

logger = logging.getLogger(__name__)

_TICK_INTERVAL = 60  # seconds — matches cron's minimum granularity


class CronScheduler:
    """Background cron scheduler that fires agent runs on schedule.

    On each tick it:
    1. Queries all ACTIVE agents with scheduled triggers
    2. For each, computes the most recent cron fire time
    3. If the fire time is newer than last_scheduled_at, creates and executes a run
    4. Updates last_scheduled_at to prevent duplicate fires
    """

    def __init__(
        self,
        pool: AsyncConnectionPool,
        execution_service: ExecutionService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._pool = pool
        self._execution_service = execution_service
        self._clock = clock or (lambda: datetime.now(UTC))
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the scheduler background task."""
        if self._task is not None:
            logger.warning("Scheduler already started")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="cairn-cron-scheduler")
        logger.info("Cron scheduler started (tick every %ds)", _TICK_INTERVAL)

    async def stop(self) -> None:
        """Stop the scheduler and wait for the current tick to finish."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Cron scheduler stopped")

    async def _loop(self) -> None:
        """Main scheduler loop. Runs until stopped."""
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Scheduler tick failed")

            try:
                await asyncio.sleep(_TICK_INTERVAL)
            except asyncio.CancelledError:
                break

    async def _tick(self) -> None:
        """Single scheduler tick: check all scheduled agents and fire those that are due."""
        now = self._clock()
        logger.debug("Scheduler tick at %s", now.isoformat())

        async with self._pool.connection() as conn:
            agents = await agent_repo.list_all(
                conn, status=AgentStatus.ACTIVE, limit=1000, offset=0
            )

        scheduled_agents = [
            a for a in agents if isinstance(a.trigger, ScheduledTrigger)
        ]

        if not scheduled_agents:
            return

        logger.debug("Found %d scheduled agents to evaluate", len(scheduled_agents))

        for agent in scheduled_agents:
            try:
                await self._evaluate_agent(agent, now)
            except Exception:
                logger.exception(
                    "Failed to evaluate schedule for agent %s (%s)",
                    agent.id,
                    agent.name,
                )

    async def _evaluate_agent(self, agent, now: datetime) -> None:
        """Check if an agent is due and fire a run if so."""
        trigger: ScheduledTrigger = agent.trigger

        try:
            tz = ZoneInfo(trigger.timezone)
        except (KeyError, ValueError):
            logger.error(
                "Invalid timezone %r for agent %s, skipping",
                trigger.timezone,
                agent.id,
            )
            return

        now_in_tz = now.astimezone(tz)
        cron = croniter(trigger.cron_expression, now_in_tz)
        most_recent_fire: datetime = cron.get_prev(datetime)
        most_recent_fire_utc = most_recent_fire.astimezone(UTC)

        async with self._pool.connection() as conn:
            last_scheduled = await schedule_repo.get_last_scheduled_at(conn, agent.id)

            if last_scheduled is not None:
                if last_scheduled.tzinfo is None:
                    last_scheduled = last_scheduled.replace(tzinfo=UTC)
                if most_recent_fire_utc <= last_scheduled:
                    return

            logger.info(
                "Cron trigger firing for agent %s (%s), fire_time=%s",
                agent.id,
                agent.name,
                most_recent_fire_utc.isoformat(),
            )

            run = AgentRun(agent_id=agent.id, input_data=None)
            run = await run_repo.create(conn, run)
            await schedule_repo.upsert_last_scheduled_at(
                conn, agent.id, most_recent_fire_utc
            )
            await conn.commit()

        asyncio.create_task(
            self._execute_run(agent, run),
            name=f"cairn-scheduled-run-{run.id}",
        )

    async def _execute_run(self, agent, run: AgentRun) -> None:
        """Execute a scheduled run using the execution service."""
        try:
            async with self._pool.connection() as conn:
                await self._execution_service.execute(agent, run, conn)
        except Exception:
            logger.exception(
                "Scheduled run %s for agent %s failed", run.id, agent.id
            )
