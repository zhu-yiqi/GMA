from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


OLD_ALARMS = (
    AlarmAsset(hour=5, minute=5, label="Old One", enabled=True, days_of_week=(), vibrate=False),
    AlarmAsset(hour=6, minute=10, label="Old Two", enabled=True, days_of_week=(), vibrate=False),
    AlarmAsset(hour=7, minute=15, label="Old Three", enabled=True, days_of_week=(), vibrate=False),
    AlarmAsset(hour=8, minute=20, label="Old Four", enabled=True, days_of_week=(), vibrate=False),
    AlarmAsset(hour=9, minute=25, label="Old Five", enabled=True, days_of_week=(), vibrate=False),
)
NEW_ALARMS = (
    AlarmAsset(hour=13, minute=0, label="Zi", enabled=True, days_of_week=("saturday",), vibrate=True),
    AlarmAsset(hour=14, minute=0, label="Chou", enabled=True, days_of_week=("saturday",), vibrate=True),
    AlarmAsset(hour=15, minute=0, label="Yin", enabled=True, days_of_week=("saturday",), vibrate=True),
    AlarmAsset(hour=16, minute=0, label="Mao", enabled=False, days_of_week=("saturday",), vibrate=True),
    AlarmAsset(hour=17, minute=0, label="Chen", enabled=False, days_of_week=("saturday",), vibrate=True),
)


class ClockReplaceFiveAlarmsSaturdayCycleTask(BaseTask):
    apps = {"Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = OLD_ALARMS
    goal = (
        "Delete the five existing Clock alarms. Then create five Saturday alarms with vibration on: "
        "Zi at 1:00 PM, Chou at 2:00 PM, Yin at 3:00 PM, Mao at 4:00 PM, and Chen at 5:00 PM. "
        "After creating them, turn off the Mao and Chen alarms."
    )

    def criteria(self):
        return [
            *(AssetDeleted(alarm, task=self) for alarm in OLD_ALARMS),
            *(AssetExists(alarm, task=self) for alarm in NEW_ALARMS),
        ]
