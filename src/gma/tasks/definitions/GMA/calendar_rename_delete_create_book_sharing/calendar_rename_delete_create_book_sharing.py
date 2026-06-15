from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset
from gma.evaluation import AssetDeleted, AssetExists, AssetModified
from gma.tasks.base import BaseTask


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


TWELVE_BEFORE = CalendarEventAsset(
    title="12",
    start_ms=_ms(2026, 10, 19, 13, 0),
    end_ms=_ms(2026, 10, 19, 14, 0),
    timezone="UTC",
)
TWELVE_AFTER = CalendarEventAsset(
    title="Meeting Day",
    start_ms=_ms(2026, 10, 19, 13, 0),
    end_ms=_ms(2026, 10, 19, 14, 0),
    timezone="UTC",
)
TA_EVENT = CalendarEventAsset(
    title="Ta",
    start_ms=_ms(2026, 11, 1, 8, 0),
    end_ms=_ms(2026, 11, 1, 9, 0),
    timezone="UTC",
)
BOOK_EVENT = CalendarEventAsset(
    title="Book Sharing Session",
    start_ms=_ms(2026, 10, 20, 9, 0),
    end_ms=_ms(2026, 10, 20, 12, 0),
    location="International Conference Center",
    description="Remember to bring books of different genres for sharing",
    timezone="UTC",
)


class CalendarRenameDeleteCreateBookSharingTask(BaseTask):
    apps = {"Calendar"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (TWELVE_BEFORE, TA_EVENT)
    user_interaction = (
        "If the agent asks which date to use for the new Book Sharing Session event, "
        "answer exactly: October 20, 2026. Do not provide unrelated information."
    )
    goal = (
        "Open Calendar, find the event titled 12, and rename it to Meeting Day. Then delete "
        "the event titled Ta on November 1, 2026. After that, create an event titled Book Sharing "
        "Session at International Conference Center from 9:00 AM to 12:00 PM, with description "
        "\"Remember to bring books of different genres for sharing\"."
    )

    def criteria(self):
        return [
            AssetModified(TWELVE_BEFORE, TWELVE_AFTER, task=self),
            AssetDeleted(TA_EVENT, task=self),
            AssetExists(BOOK_EVENT, task=self),
        ]
