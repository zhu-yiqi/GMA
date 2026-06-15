from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


CONCERT_COUNTDOWN_BEFORE = CalendarEventAsset(
    title="Concert Countdown",
    start_ms=_ms(2026, 10, 20, 17, 0),
    end_ms=_ms(2026, 10, 20, 18, 0),
    location="New York",
    timezone="UTC",
)
CONCERT_COUNTDOWN_AFTER = CalendarEventAsset(
    title="Concert Countdown",
    start_ms=CONCERT_COUNTDOWN_BEFORE.start_ms,
    end_ms=_ms(2026, 10, 20, 19, 0),
    location="Denver",
    timezone="UTC",
)
DRAGON_BOAT_PLANNING = CalendarEventAsset(
    title="River Festival Planning",
    start_ms=_ms(2026, 10, 21, 10, 0),
    end_ms=_ms(2026, 10, 21, 11, 0),
    location="Community Center",
    timezone="UTC",
)


class CalendarUpdateConcertCountdownTask(BaseTask):
    apps = {"Calendar"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (CONCERT_COUNTDOWN_BEFORE, DRAGON_BOAT_PLANNING)
    goal = (
        "In Calendar, find the existing event 'Concert Countdown' on October 20, 2026. "
        "Change its end time to 7:00 PM and change its location to Denver."
    )

    def criteria(self):
        return [AssetModified(CONCERT_COUNTDOWN_BEFORE, CONCERT_COUNTDOWN_AFTER, task=self)]
