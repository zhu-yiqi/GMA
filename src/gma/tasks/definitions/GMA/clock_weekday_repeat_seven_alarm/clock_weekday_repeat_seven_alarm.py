from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


BREAKFAST_REMINDER_BEFORE = AlarmAsset(
    hour=7,
    minute=0,
    label="Breakfast Reminder",
    enabled=True,
    days_of_week=("saturday",),
)
BREAKFAST_REMINDER_AFTER = AlarmAsset(
    hour=BREAKFAST_REMINDER_BEFORE.hour,
    minute=BREAKFAST_REMINDER_BEFORE.minute,
    label=BREAKFAST_REMINDER_BEFORE.label,
    enabled=True,
    days_of_week=("monday", "tuesday", "wednesday", "thursday", "friday"),
)


class ClockWeekdayRepeatSevenAlarmTask(BaseTask):
    apps = {"Clock"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (BREAKFAST_REMINDER_BEFORE,)
    goal = (
        "Find the 7:00 AM Clock alarm labeled 'Breakfast Reminder' "
        "and make it repeat Monday through Friday."
    )

    def criteria(self):
        return [AssetModified(BREAKFAST_REMINDER_BEFORE, BREAKFAST_REMINDER_AFTER, task=self)]
