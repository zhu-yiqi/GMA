from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


CHILDRENS_DAY_BEFORE = CalendarEventAsset(
    title="Weekend Music Practice",
    start_ms=_ms(2026, 10, 3, 17, 0),
    end_ms=_ms(2026, 10, 3, 18, 0),
    timezone="UTC",
)
CHILDRENS_DAY_AFTER = CalendarEventAsset(
    title="Music Festival Countdown",
    start_ms=_ms(2026, 10, 3, 17, 0),
    end_ms=_ms(2026, 10, 3, 19, 0),
    timezone="UTC",
)


class CalendarWeekendMusicPracticeCountdownTask(BaseTask):
    apps = {"Calendar"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (CHILDRENS_DAY_BEFORE,)
    goal = (
        "Open Calendar and find the existing Weekend Music Practice event on October 3, 2026. If it exists, "
        "rename it to Music Festival Countdown and change its end time to 7:00 PM on October 3, 2026. "
        "If it does not exist, create it with the same title and end time, starting at 5:00 PM."
    )

    def criteria(self):
        return [AssetModified(CHILDRENS_DAY_BEFORE, CHILDRENS_DAY_AFTER, task=self)]
