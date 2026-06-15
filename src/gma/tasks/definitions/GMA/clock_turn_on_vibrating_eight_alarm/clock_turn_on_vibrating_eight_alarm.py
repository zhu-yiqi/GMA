from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


VIBRATING_BEFORE = AlarmAsset(
    hour=8,
    minute=0,
    label="Vibrating Eight",
    enabled=False,
    days_of_week=(),
    vibrate=True,
)
VIBRATING_AFTER = AlarmAsset(
    hour=8,
    minute=0,
    label="Vibrating Eight",
    enabled=True,
    days_of_week=(),
    vibrate=True,
)
QUIET_EIGHT = AlarmAsset(
    hour=8,
    minute=0,
    label="Quiet Eight",
    enabled=False,
    days_of_week=(),
    vibrate=False,
)


class ClockTurnOnVibratingEightAlarmTask(BaseTask):
    apps = {"Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (VIBRATING_BEFORE, QUIET_EIGHT)
    goal = "Turn on the 8:00 AM Clock alarm that already has vibration enabled."

    def criteria(self):
        return [
            AssetModified(VIBRATING_BEFORE, VIBRATING_AFTER, task=self),
            AssetExists(QUIET_EIGHT, task=self),
        ]
