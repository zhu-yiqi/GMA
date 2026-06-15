from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset, ContactAsset, SmsMessageAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


WORKDAY = CalendarEventAsset(
    title="Workday",
    start_ms=_ms(2026, 10, 26, 8, 0),
    end_ms=_ms(2026, 10, 26, 21, 0),
    description="Looking forward to rest",
    timezone="UTC",
)
NOVEMBER_BEFORE = CalendarEventAsset(
    title="November Plan",
    start_ms=_ms(2026, 11, 1, 10, 0),
    end_ms=_ms(2026, 11, 1, 12, 0),
    description="Original note",
    timezone="UTC",
)
NOVEMBER_AFTER = CalendarEventAsset(
    title="Busy",
    start_ms=_ms(2026, 11, 1, 9, 0),
    end_ms=_ms(2026, 11, 1, 18, 0),
    description="International Children's Day",
    timezone="UTC",
)
CONTACT = ContactAsset(name="Schedule Contact", phone_number="5550101008")
NOTICE = SmsMessageAsset(
    address="5550101008",
    body="Schedule updated: Busy on November 1 from 9:00 AM to 6:00 PM.",
    box="sent",
    read=True,
)


class CalendarUpdateNovemberEventSmsNoticeTask(BaseTask):
    apps = {"Calendar", "Messages"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (NOVEMBER_BEFORE, CONTACT)
    goal = (
        "In Calendar, create an event titled Workday on October 26, 2026 from 8:00 AM "
        "to 9:00 PM with description \"Looking forward to rest\". Then modify the existing "
        "November 1 event so it runs from 9:00 AM to 6:00 PM, its title is Busy, and its "
        "description is \"International Children's Day\". Finally, send an SMS to 5550101008 "
        "with exactly this message: \"Schedule updated: Busy on November 1 from 9:00 AM to 6:00 PM.\""
    )

    def criteria(self):
        return [
            AssetExists(WORKDAY, task=self),
            AssetModified(NOVEMBER_BEFORE, NOVEMBER_AFTER, task=self),
            AssetExists(NOTICE, task=self),
        ]
