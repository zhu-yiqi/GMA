from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MORNING_ALARM = AlarmAsset(
    hour=6,
    minute=0,
    label="Morning Alarm",
    enabled=True,
)


class ClockCreateMorningAlarmTask(BaseTask):
    apps = {"Clock"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = ()
    goal = "Create a Clock alarm for 6:00 AM labeled 'Morning Alarm'."

    def criteria(self):
        return [AssetExists(MORNING_ALARM, task=self)]
