from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


MORNING_LABEL_BEFORE = AlarmAsset(
    hour=6,
    minute=30,
    label="Morning",
    enabled=True,
)
MORNING_LABEL_AFTER = AlarmAsset(
    hour=MORNING_LABEL_BEFORE.hour,
    minute=MORNING_LABEL_BEFORE.minute,
    label="Time to Get Up",
    enabled=True,
)


class ClockRenameMorningAlarmTask(BaseTask):
    apps = {"Clock"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (MORNING_LABEL_BEFORE,)
    goal = "Find the Clock alarm labeled 'Morning' and change its label to 'Time to Get Up'."

    def criteria(self):
        return [AssetModified(MORNING_LABEL_BEFORE, MORNING_LABEL_AFTER, task=self)]
