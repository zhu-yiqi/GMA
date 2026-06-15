from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


CONCERT_EVENT = CalendarEventAsset(
    title="Concert",
    start_ms=_ms(2026, 10, 3, 8, 0),
    end_ms=_ms(2026, 10, 4, 18, 0),
    location="MetLife Stadium",
    timezone="UTC",
)


class CalendarCreateConcertBirdsnestTask(BaseTask):
    apps = {"Calendar"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = ()
    goal = (
        "Create a Calendar event titled 'Concert' at MetLife Stadium "
        "from Saturday, October 3, 2026 at 8:00 AM to Sunday, October 4, 2026 at 6:00 PM."
    )

    def criteria(self):
        return [AssetExists(CONCERT_EVENT, task=self)]
