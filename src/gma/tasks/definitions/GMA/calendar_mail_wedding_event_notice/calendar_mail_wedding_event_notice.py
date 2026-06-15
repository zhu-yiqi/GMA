from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset, MailMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


def _ms(year: int, month: int, day: int, hour: int, minute: int) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


WEDDING_EVENT = CalendarEventAsset(
    title="A friend's wedding",
    start_ms=_ms(2026, 10, 10, 7, 0),
    end_ms=_ms(2026, 10, 10, 12, 0),
    location="Austin",
    description="attending a friend's wedding",
    timezone="UTC",
    reminder_minutes=(60,),
)
WEDDING_MAIL = MailMessageAsset(
    mailbox="sent",
    from_email="test@gmail.com",
    to=["skycy@gmail.com"],
    subject="A friend's wedding",
    body="Wedding notice: A friend's wedding is in Austin on October 10, 2026 from 7:00 AM to 12:00 PM.",
)


class CalendarMailWeddingEventNoticeTask(BaseTask):
    apps = {"Calendar", "Mail"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    goal = (
        "Open Calendar and create an event titled \"A friend's wedding\" at Austin on "
        "October 10, 2026 from 7:00 AM to 12:00 PM. Set the description to "
        "\"attending a friend's wedding\" and set a reminder 1 hour before it starts. "
        "Then open Mail and send the event time and location to skycy@gmail.com with subject "
        "\"A friend's wedding\" and exactly this body: \"Wedding notice: A friend's wedding "
        "is in Austin on October 10, 2026 from 7:00 AM to 12:00 PM.\""
    )

    def criteria(self):
        return [
            AssetExists(WEDDING_EVENT, task=self),
            AssetExists(WEDDING_MAIL, task=self),
        ]
