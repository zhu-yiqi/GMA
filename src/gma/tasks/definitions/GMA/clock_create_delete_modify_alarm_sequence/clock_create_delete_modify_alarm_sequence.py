from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetDeleted, AssetExists, AssetModified
from gma.tasks.base import BaseTask


NEW_TUESDAY_ALARM = AlarmAsset(
    hour=8,
    minute=0,
    label="Tuesday Morning",
    enabled=True,
    days_of_week=("tuesday",),
    vibrate=True,
)
GET_UP_ALARM = AlarmAsset(
    hour=6,
    minute=30,
    label="Get Up",
    enabled=True,
    days_of_week=("monday", "tuesday", "wednesday", "thursday", "friday"),
    vibrate=True,
)
A_BEFORE = AlarmAsset(
    hour=8,
    minute=30,
    label="A",
    enabled=True,
    days_of_week=("wednesday",),
    vibrate=True,
)
A_AFTER = AlarmAsset(
    hour=15,
    minute=30,
    label="A",
    enabled=True,
    days_of_week=("thursday",),
    vibrate=False,
)


class ClockCreateDeleteModifyAlarmSequenceTask(BaseTask):
    apps = {"Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (GET_UP_ALARM, A_BEFORE)
    user_interaction = (
        "If the agent asks what time to use for the new Tuesday morning alarm, "
        "answer exactly: 8:00 AM. Do not provide unrelated information."
    )
    goal = (
        "Create a morning Clock alarm labeled Tuesday Morning that repeats every Tuesday "
        "and has vibration enabled. Then delete the alarm labeled Get Up. Finally, change "
        "the alarm labeled A from 8:30 AM to 3:30 PM, change its repeat day from Wednesday "
        "to Thursday, and turn vibration off."
    )

    def criteria(self):
        return [
            AssetExists(NEW_TUESDAY_ALARM, task=self),
            AssetDeleted(GET_UP_ALARM, task=self),
            AssetModified(A_BEFORE, A_AFTER, task=self),
        ]
