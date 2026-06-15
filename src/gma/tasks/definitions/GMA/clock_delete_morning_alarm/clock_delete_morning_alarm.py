from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


MORNING_ALARM = AlarmAsset(
    hour=6,
    minute=0,
    label="Morning Alarm",
    enabled=True,
)


class ClockDeleteMorningAlarmTask(BaseTask):
    apps = {"Clock"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (MORNING_ALARM,)
    goal = "Delete the 6:00 AM Clock alarm labeled 'Morning Alarm'."

    def criteria(self):
        return [AssetDeleted(MORNING_ALARM, task=self)]
