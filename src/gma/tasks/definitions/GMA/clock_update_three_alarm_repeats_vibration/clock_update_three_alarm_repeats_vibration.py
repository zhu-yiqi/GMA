from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


A_BEFORE = AlarmAsset(hour=6, minute=10, label="A", enabled=True, days_of_week=("saturday",), vibrate=True)
A_AFTER = AlarmAsset(
    hour=6,
    minute=10,
    label="A",
    enabled=True,
    days_of_week=("monday", "tuesday", "wednesday", "thursday", "friday"),
    vibrate=False,
)
B_BEFORE = AlarmAsset(hour=7, minute=20, label="B", enabled=True, days_of_week=("sunday",), vibrate=True)
B_AFTER = AlarmAsset(
    hour=7,
    minute=20,
    label="B",
    enabled=True,
    days_of_week=("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
    vibrate=False,
)
C_BEFORE = AlarmAsset(hour=8, minute=30, label="C", enabled=True, days_of_week=(), vibrate=False)
C_AFTER = AlarmAsset(hour=8, minute=30, label="C", enabled=True, days_of_week=(), vibrate=True)


class ClockUpdateThreeAlarmRepeatsVibrationTask(BaseTask):
    apps = {"Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (A_BEFORE, B_BEFORE, C_BEFORE)
    goal = (
        "In Clock, update alarm A so it repeats Monday through Friday and vibration is off. "
        "Update alarm B so it repeats every day and vibration is off. Then turn vibration on "
        "for alarm C."
    )

    def criteria(self):
        return [
            AssetModified(A_BEFORE, A_AFTER, task=self),
            AssetModified(B_BEFORE, B_AFTER, task=self),
            AssetModified(C_BEFORE, C_AFTER, task=self),
        ]
