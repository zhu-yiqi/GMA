from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset, MailAccountAsset, MailMessageAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


def utc_ms(year: int, month: int, day: int, hour: int, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


MAIL_BODY = (
    "I just remembered I have another commitment that day and have already scheduled a photo shoot "
    "with my instructor, so I will have to temporarily postpone the birthday gathering."
)


class CalendarMailComicExpoUpdateTask(BaseTask):
    apps = {"Calendar", "Mail"}
    difficulty = "hard"
    snapshot = "gma_ready_state"

    before_event = CalendarEventAsset(
        title="Alex Parker's Birthday",
        start_ms=utc_ms(2026, 10, 6, 9, 30),
        end_ms=utc_ms(2026, 10, 6, 10, 30),
        description="Birthday gathering planning note",
        timezone="UTC",
    )
    after_event = CalendarEventAsset(
        title="ACG Comic Expo",
        start_ms=utc_ms(2026, 10, 6, 10, 0),
        end_ms=utc_ms(2026, 10, 6, 18, 0),
        location="International Convention and Exhibition Center",
        description="Comic Expo",
        timezone="UTC",
        reminder_minutes=(0,),
    )
    account = MailAccountAsset(
        display_name="Parker Grant",
        email="calendar.mail.user@example.com",
    )
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["skycy@gmail.com"],
        subject="Comic Expo Postpones Birthday Gathering",
        body=MAIL_BODY,
        read=True,
    )
    assets = (before_event, account)

    goal = (
        "Open Calendar, find the event titled \"Alex Parker's Birthday\", and update it to title "
        "\"ACG Comic Expo\" at \"International Convention and Exhibition Center\" from 10:00 AM "
        "to 6:00 PM on October 6, 2026. Set the description to \"Comic Expo\" and add an at-start reminder. "
        "Then open Mail and send skycy@gmail.com an email with subject "
        "\"Comic Expo Postpones Birthday Gathering\" and body "
        f"\"{MAIL_BODY}\"."
    )

    def criteria(self):
        return [
            AssetModified(self.before_event, self.after_event, task=self),
            AssetExists(self.expected_mail, task=self),
        ]
