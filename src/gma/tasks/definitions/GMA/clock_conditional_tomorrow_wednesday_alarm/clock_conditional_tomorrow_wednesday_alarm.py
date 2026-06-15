from __future__ import annotations

from gma.assets import AlarmAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


EIGHT_AM_ALARM = AlarmAsset(
    hour=8,
    minute=0,
    label="Wednesday Check",
    enabled=False,
    days_of_week=(),
    vibrate=False,
)


class ClockConditionalTomorrowWednesdayAlarmTask(BaseTask):
    apps = {"Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (EIGHT_AM_ALARM,)
    goal = (
        "Check whether there is an 8:00 AM Clock alarm. If tomorrow is not Wednesday, "
        "turn that alarm on; otherwise leave it off."
    )

    def criteria(self):
        return [AssetExists(EIGHT_AM_ALARM.model_copy(update={"enabled": True}), task=self)]
