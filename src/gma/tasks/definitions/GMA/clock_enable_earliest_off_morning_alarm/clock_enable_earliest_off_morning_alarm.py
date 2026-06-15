from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


EARLIEST_BEFORE = AlarmAsset(
    hour=7,
    minute=15,
    label="Early Errand",
    enabled=False,
    days_of_week=(),
    vibrate=False,
)
EARLIEST_AFTER = AlarmAsset(
    hour=7,
    minute=15,
    label="Early Errand",
    enabled=True,
    days_of_week=(),
    vibrate=True,
    scheduled_year=2026,
    scheduled_month=10,
    scheduled_day=2,
)
LATER_OFF = AlarmAsset(
    hour=9,
    minute=30,
    label="Late Morning",
    enabled=False,
    days_of_week=(),
    vibrate=False,
)
REPEATING_OFF = AlarmAsset(
    hour=6,
    minute=45,
    label="Repeat Morning",
    enabled=False,
    days_of_week=("friday",),
    vibrate=False,
)


class ClockEnableEarliestOffMorningAlarmTask(BaseTask):
    apps = {"Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (EARLIEST_BEFORE, LATER_OFF, REPEATING_OFF)
    goal = (
        "Find the earliest Clock alarm that is currently off and does not repeat. "
        "Turn it on, schedule it for tomorrow, and enable vibration."
    )

    def criteria(self):
        return [
            AssetModified(EARLIEST_BEFORE, EARLIEST_AFTER, task=self),
            AssetExists(LATER_OFF, task=self),
            AssetExists(REPEATING_OFF, task=self),
        ]
