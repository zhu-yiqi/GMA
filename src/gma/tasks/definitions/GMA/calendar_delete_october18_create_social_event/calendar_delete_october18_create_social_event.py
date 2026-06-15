from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


OLD_OCTOBER_EVENT = CalendarEventAsset(
    title="October 18 Planning",
    start_ms=_ms(2026, 10, 18, 10, 0),
    end_ms=_ms(2026, 10, 18, 11, 0),
    timezone="UTC",
)
SOCIAL_EVENT = CalendarEventAsset(
    title="Campus Social Event",
    start_ms=_ms(2026, 10, 19, 9, 0),
    end_ms=_ms(2026, 10, 19, 16, 0),
    location="School",
    timezone="UTC",
    reminder_minutes=(0,),
)


class CalendarDeleteOctober18CreateSocialEventTask(BaseTask):
    apps = {"Calendar"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (OLD_OCTOBER_EVENT,)
    goal = (
        "Open Calendar, delete the event on October 18, 2026 titled October 18 Planning, "
        "then create an event on October 19, 2026 titled Campus Social Event at School "
        "from 9:00 AM to 4:00 PM with a reminder at the start time."
    )

    def criteria(self):
        return [
            AssetDeleted(OLD_OCTOBER_EVENT, task=self),
            AssetExists(SOCIAL_EVENT, task=self),
        ]
