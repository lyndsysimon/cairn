"""Tests for cron expression and timezone validation on ScheduledTrigger."""

import pytest
from pydantic import ValidationError

from cairn.models.trigger import ScheduledTrigger


class TestCronExpressionValidation:
    def test_valid_cron_expressions(self):
        for expr in ["* * * * *", "*/5 * * * *", "0 9 * * 1-5", "0 0 1 * *"]:
            trigger = ScheduledTrigger(cron_expression=expr)
            assert trigger.cron_expression == expr

    def test_invalid_cron_expression_rejected(self):
        with pytest.raises(ValidationError, match="Invalid cron expression"):
            ScheduledTrigger(cron_expression="not-a-cron")

    def test_empty_cron_expression_rejected(self):
        with pytest.raises(ValidationError, match="Invalid cron expression"):
            ScheduledTrigger(cron_expression="")


class TestTimezoneValidation:
    def test_default_utc(self):
        trigger = ScheduledTrigger(cron_expression="* * * * *")
        assert trigger.timezone == "UTC"

    def test_valid_timezone(self):
        trigger = ScheduledTrigger(
            cron_expression="* * * * *", timezone="America/New_York"
        )
        assert trigger.timezone == "America/New_York"

    def test_invalid_timezone_rejected(self):
        with pytest.raises(ValidationError, match="Invalid timezone"):
            ScheduledTrigger(
                cron_expression="* * * * *", timezone="Not/A/Timezone"
            )
