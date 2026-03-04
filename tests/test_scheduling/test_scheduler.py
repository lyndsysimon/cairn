"""Tests for the cron scheduler.

Uses a controllable clock and mocked database/execution layers.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cairn.models.agent import AgentDefinition, AgentStatus
from cairn.models.run import AgentRun
from cairn.models.runtime import RuntimeConfig, RuntimeType
from cairn.models.trigger import ManualTrigger, ScheduledTrigger
from cairn.scheduling.scheduler import CronScheduler


def _make_scheduled_agent(
    cron_expression: str = "*/5 * * * *",
    timezone: str = "UTC",
    status: AgentStatus = AgentStatus.ACTIVE,
) -> AgentDefinition:
    return AgentDefinition(
        name="scheduled-agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger=ScheduledTrigger(
            cron_expression=cron_expression,
            timezone=timezone,
        ),
        runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
        status=status,
    )


def _make_manual_agent() -> AgentDefinition:
    return AgentDefinition(
        name="manual-agent",
        model_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger=ManualTrigger(),
        runtime=RuntimeConfig(type=RuntimeType.DOCKER, image="python:3.13-slim"),
    )


def _make_pool():
    """Create a mock AsyncConnectionPool that yields a mock connection."""
    conn = AsyncMock()
    conn.commit = AsyncMock()

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=False)

    pool = MagicMock()
    pool.connection.return_value = cm

    return pool, conn


class TestSchedulerTick:
    """Test the _tick() method directly with a controlled clock."""

    @pytest.mark.asyncio
    async def test_fires_due_agent(self):
        """An agent whose cron fire time is newer than last_scheduled_at gets a run."""
        agent = _make_scheduled_agent("*/5 * * * *")
        pool, conn = _make_pool()
        service = AsyncMock()

        # Clock at 12:07 — the cron "*/5" last fired at 12:05
        now = datetime(2026, 3, 4, 12, 7, 0, tzinfo=UTC)
        scheduler = CronScheduler(pool, service, clock=lambda: now)

        with (
            patch("cairn.scheduling.scheduler.agent_repo") as mock_agent_repo,
            patch("cairn.scheduling.scheduler.run_repo") as mock_run_repo,
            patch("cairn.scheduling.scheduler.schedule_repo") as mock_sched_repo,
        ):
            mock_agent_repo.list_all = AsyncMock(return_value=[agent])
            mock_sched_repo.get_last_scheduled_at = AsyncMock(return_value=None)
            mock_sched_repo.upsert_last_scheduled_at = AsyncMock()
            mock_run_repo.create = AsyncMock(
                return_value=AgentRun(agent_id=agent.id)
            )

            await scheduler._tick()

            mock_run_repo.create.assert_called_once()
            mock_sched_repo.upsert_last_scheduled_at.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_already_fired(self):
        """An agent that already fired for this interval should not fire again."""
        agent = _make_scheduled_agent("*/5 * * * *")
        pool, conn = _make_pool()
        service = AsyncMock()

        now = datetime(2026, 3, 4, 12, 7, 0, tzinfo=UTC)
        scheduler = CronScheduler(pool, service, clock=lambda: now)

        with (
            patch("cairn.scheduling.scheduler.agent_repo") as mock_agent_repo,
            patch("cairn.scheduling.scheduler.run_repo") as mock_run_repo,
            patch("cairn.scheduling.scheduler.schedule_repo") as mock_sched_repo,
        ):
            mock_agent_repo.list_all = AsyncMock(return_value=[agent])
            # Last scheduled at 12:05 — same as the cron fire time
            mock_sched_repo.get_last_scheduled_at = AsyncMock(
                return_value=datetime(2026, 3, 4, 12, 5, 0, tzinfo=UTC)
            )

            await scheduler._tick()

            mock_run_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_manual_trigger(self):
        """Agents with ManualTrigger are ignored by the scheduler."""
        agent = _make_manual_agent()
        pool, conn = _make_pool()
        service = AsyncMock()

        scheduler = CronScheduler(pool, service)

        with (
            patch("cairn.scheduling.scheduler.agent_repo") as mock_agent_repo,
            patch("cairn.scheduling.scheduler.run_repo") as mock_run_repo,
            patch("cairn.scheduling.scheduler.schedule_repo") as mock_sched_repo,
        ):
            mock_agent_repo.list_all = AsyncMock(return_value=[agent])

            await scheduler._tick()

            mock_run_repo.create.assert_not_called()
            mock_sched_repo.get_last_scheduled_at.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_in_one_agent_doesnt_block_others(self):
        """Exception in one agent doesn't prevent others from firing."""
        good_agent = _make_scheduled_agent("*/5 * * * *")
        bad_agent = _make_scheduled_agent("*/5 * * * *")

        pool, conn = _make_pool()
        service = AsyncMock()

        now = datetime(2026, 3, 4, 12, 7, 0, tzinfo=UTC)
        scheduler = CronScheduler(pool, service, clock=lambda: now)

        call_count = 0

        async def mock_get_last_scheduled(conn, agent_id):
            nonlocal call_count
            call_count += 1
            if agent_id == bad_agent.id:
                raise RuntimeError("DB exploded")
            return None

        with (
            patch("cairn.scheduling.scheduler.agent_repo") as mock_agent_repo,
            patch("cairn.scheduling.scheduler.run_repo") as mock_run_repo,
            patch("cairn.scheduling.scheduler.schedule_repo") as mock_sched_repo,
        ):
            mock_agent_repo.list_all = AsyncMock(
                return_value=[bad_agent, good_agent]
            )
            mock_sched_repo.get_last_scheduled_at = AsyncMock(
                side_effect=mock_get_last_scheduled
            )
            mock_sched_repo.upsert_last_scheduled_at = AsyncMock()
            mock_run_repo.create = AsyncMock(
                return_value=AgentRun(agent_id=good_agent.id)
            )

            await scheduler._tick()

            # The good agent should still have been processed
            mock_run_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_scheduled_agents(self):
        """Tick with no scheduled agents should be a no-op."""
        pool, conn = _make_pool()
        service = AsyncMock()
        scheduler = CronScheduler(pool, service)

        with (
            patch("cairn.scheduling.scheduler.agent_repo") as mock_agent_repo,
            patch("cairn.scheduling.scheduler.schedule_repo") as mock_sched_repo,
        ):
            mock_agent_repo.list_all = AsyncMock(return_value=[])

            await scheduler._tick()

            mock_sched_repo.get_last_scheduled_at.assert_not_called()

    @pytest.mark.asyncio
    async def test_respects_timezone(self):
        """Cron with non-UTC timezone is evaluated correctly."""
        # Agent fires every hour at :00 in America/New_York
        agent = _make_scheduled_agent("0 * * * *", timezone="America/New_York")
        pool, conn = _make_pool()
        service = AsyncMock()

        # 17:30 UTC = 12:30 Eastern — last hourly fire was 12:00 Eastern = 17:00 UTC
        now = datetime(2026, 3, 4, 17, 30, 0, tzinfo=UTC)
        scheduler = CronScheduler(pool, service, clock=lambda: now)

        with (
            patch("cairn.scheduling.scheduler.agent_repo") as mock_agent_repo,
            patch("cairn.scheduling.scheduler.run_repo") as mock_run_repo,
            patch("cairn.scheduling.scheduler.schedule_repo") as mock_sched_repo,
        ):
            mock_agent_repo.list_all = AsyncMock(return_value=[agent])
            # Last scheduled at 16:00 UTC (11:00 Eastern)
            mock_sched_repo.get_last_scheduled_at = AsyncMock(
                return_value=datetime(2026, 3, 4, 16, 0, 0, tzinfo=UTC)
            )
            mock_sched_repo.upsert_last_scheduled_at = AsyncMock()
            mock_run_repo.create = AsyncMock(
                return_value=AgentRun(agent_id=agent.id)
            )

            await scheduler._tick()

            # Should fire because 17:00 UTC > 16:00 UTC
            mock_run_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_timezone_skipped(self):
        """Agent with invalid timezone is logged and skipped, not crashed."""
        agent = _make_scheduled_agent("*/5 * * * *")
        # Override the trigger with an invalid timezone (bypass validator for test)
        agent = agent.model_copy(
            update={
                "trigger": ScheduledTrigger.model_construct(
                    type="scheduled",
                    cron_expression="*/5 * * * *",
                    timezone="Not/A/Timezone",
                )
            }
        )
        pool, conn = _make_pool()
        service = AsyncMock()

        now = datetime(2026, 3, 4, 12, 7, 0, tzinfo=UTC)
        scheduler = CronScheduler(pool, service, clock=lambda: now)

        with (
            patch("cairn.scheduling.scheduler.agent_repo") as mock_agent_repo,
            patch("cairn.scheduling.scheduler.run_repo") as mock_run_repo,
            patch("cairn.scheduling.scheduler.schedule_repo"),
        ):
            mock_agent_repo.list_all = AsyncMock(return_value=[agent])

            # Should not raise
            await scheduler._tick()

            mock_run_repo.create.assert_not_called()


class TestSchedulerLifecycle:
    """Test start/stop behavior."""

    @pytest.mark.asyncio
    async def test_start_creates_task(self):
        pool, _ = _make_pool()
        service = AsyncMock()
        scheduler = CronScheduler(pool, service)

        await scheduler.start()
        assert scheduler._task is not None
        assert not scheduler._task.done()

        await scheduler.stop()
        assert scheduler._task is None

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self):
        pool, _ = _make_pool()
        service = AsyncMock()
        scheduler = CronScheduler(pool, service)

        # Calling stop without start should not raise
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_double_start_warns(self):
        pool, _ = _make_pool()
        service = AsyncMock()
        scheduler = CronScheduler(pool, service)

        await scheduler.start()
        await scheduler.start()  # Should not create a second task

        await scheduler.stop()
