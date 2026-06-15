from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


A_BEFORE = AlarmAsset(hour=7, minute=0, label="A", enabled=True, days_of_week=(), vibrate=True)
A_AFTER = AlarmAsset(hour=7, minute=0, label="Morning", enabled=True, days_of_week=(), vibrate=True)
B_BEFORE = AlarmAsset(hour=12, minute=0, label="B", enabled=True, days_of_week=(), vibrate=True)
B_AFTER = AlarmAsset(hour=12, minute=0, label="Noon", enabled=False, days_of_week=(), vibrate=True)
C_BEFORE = AlarmAsset(hour=15, minute=0, label="C", enabled=True, days_of_week=(), vibrate=False)
C_AFTER = AlarmAsset(hour=15, minute=0, label="Afternoon", enabled=False, days_of_week=(), vibrate=False)
EVENING_BEFORE = AlarmAsset(hour=20, minute=0, label="Evening", enabled=True, days_of_week=("friday",), vibrate=False)
EVENING_AFTER = AlarmAsset(
    hour=20,
    minute=0,
    label="Evening",
    enabled=True,
    days_of_week=("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
    vibrate=True,
)


class ClockRenameDisableEveningDailyTask(BaseTask):
    apps = {"Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (A_BEFORE, B_BEFORE, C_BEFORE, EVENING_BEFORE)
    goal = (
        "In Clock, rename alarm A to Morning, alarm B to Noon, and alarm C to Afternoon. "
        "Turn off the Noon and Afternoon alarms. Then enable vibration for the Evening alarm "
        "and make the Evening alarm repeat every day."
    )

    def criteria(self):
        return [
            AssetModified(A_BEFORE, A_AFTER, task=self),
            AssetModified(B_BEFORE, B_AFTER, task=self),
            AssetModified(C_BEFORE, C_AFTER, task=self),
            AssetModified(EVENING_BEFORE, EVENING_AFTER, task=self),
        ]
