from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


BIRTHDAY_EVENT = CalendarEventAsset(
    title="Birthday Dinner",
    start_ms=_ms(2026, 10, 12, 18, 0),
    end_ms=_ms(2026, 10, 12, 20, 0),
    location="Maple Cafe",
    timezone="UTC",
)


class CalendarDeleteBirthdayDinnerTask(BaseTask):
    apps = {"Calendar"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (BIRTHDAY_EVENT,)
    goal = "Delete the existing Calendar event titled 'Birthday Dinner'."

    def criteria(self):
        return [AssetDeleted(BIRTHDAY_EVENT, task=self)]
