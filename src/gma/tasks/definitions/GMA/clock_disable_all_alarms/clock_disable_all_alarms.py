from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


EARLY_WORKOUT_ON = AlarmAsset(
    hour=6,
    minute=20,
    label="Early Workout",
    enabled=True,
)
EVENING_CHECK_ON = AlarmAsset(
    hour=21,
    minute=15,
    label="Evening Check",
    enabled=True,
)
EARLY_WORKOUT_OFF = AlarmAsset(
    hour=EARLY_WORKOUT_ON.hour,
    minute=EARLY_WORKOUT_ON.minute,
    label=EARLY_WORKOUT_ON.label,
    enabled=False,
)
EVENING_CHECK_OFF = AlarmAsset(
    hour=EVENING_CHECK_ON.hour,
    minute=EVENING_CHECK_ON.minute,
    label=EVENING_CHECK_ON.label,
    enabled=False,
)


class ClockDisableAllAlarmsTask(BaseTask):
    apps = {"Clock"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (EARLY_WORKOUT_ON, EVENING_CHECK_ON)
    goal = "Turn off every alarm in Clock."

    def criteria(self):
        return [
            AssetModified(EARLY_WORKOUT_ON, EARLY_WORKOUT_OFF, task=self),
            AssetModified(EVENING_CHECK_ON, EVENING_CHECK_OFF, task=self),
        ]
