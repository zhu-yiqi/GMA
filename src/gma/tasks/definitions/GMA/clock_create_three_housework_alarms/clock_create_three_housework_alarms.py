from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


COOKING = AlarmAsset(hour=15, minute=0, label="Cooking Time", enabled=True, days_of_week=(), vibrate=True)
LAUNDRY = AlarmAsset(hour=18, minute=0, label="Hang Clothes", enabled=True, days_of_week=(), vibrate=True)
BREAKFAST = AlarmAsset(
    hour=7,
    minute=0,
    label="Make Breakfast",
    enabled=True,
    days_of_week=("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
    vibrate=True,
)


class ClockCreateThreeHouseworkAlarmsTask(BaseTask):
    apps = {"Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    goal = (
        "Create three Clock alarms: Cooking Time at 3:00 PM with no repeat and vibration on; "
        "Hang Clothes at 6:00 PM with no repeat and vibration on; and Make Breakfast at 7:00 AM "
        "repeating every day with vibration on."
    )

    def criteria(self):
        return [
            AssetExists(COOKING, task=self),
            AssetExists(LAUNDRY, task=self),
            AssetExists(BREAKFAST, task=self),
        ]
