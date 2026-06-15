from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


A_BEFORE = AlarmAsset(
    hour=9,
    minute=0,
    label="A",
    enabled=True,
    days_of_week=("thursday",),
    vibrate=True,
)
A_AFTER = AlarmAsset(
    hour=9,
    minute=0,
    label="A",
    enabled=True,
    days_of_week=("thursday",),
    vibrate=False,
)
B_THURSDAY = AlarmAsset(
    hour=10,
    minute=0,
    label="B",
    enabled=True,
    days_of_week=("thursday",),
    vibrate=True,
)


class ClockDisableVibrationForThursdayAlarmATask(BaseTask):
    apps = {"Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (A_BEFORE, B_THURSDAY)
    user_interaction = (
        "If the agent asks which Thursday alarm should have vibration turned off, "
        "answer exactly: A. Do not provide unrelated information."
    )
    goal = "Turn off vibration for the Thursday Clock alarm."

    def criteria(self):
        return [
            AssetModified(A_BEFORE, A_AFTER, task=self),
            AssetExists(B_THURSDAY, task=self),
        ]
