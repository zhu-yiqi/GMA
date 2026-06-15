from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import AlarmAsset, CalendarEventAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


HIKING_ALARM = AlarmAsset(
    hour=9,
    minute=0,
    label="Hiking",
    enabled=True,
    days_of_week=(),
    vibrate=True,
    scheduled_year=2026,
    scheduled_month=10,
    scheduled_day=2,
)
HIKING_EVENT = CalendarEventAsset(
    title="Hiking",
    start_ms=_ms(2026, 10, 2, 9, 0),
    end_ms=_ms(2026, 10, 2, 9, 0),
    description="Must go",
    timezone="UTC",
)


class ClockCalendarTomorrowHikingReminderTask(BaseTask):
    apps = {"Clock", "Calendar"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    goal = (
        "Create a Clock alarm for 9:00 AM tomorrow labeled Hiking with vibration enabled. "
        "Then add a Calendar event for that same time with title Hiking and description "
        "\"Must go\"."
    )

    def criteria(self):
        return [
            AssetExists(HIKING_ALARM, task=self),
            AssetExists(HIKING_EVENT, task=self),
        ]
