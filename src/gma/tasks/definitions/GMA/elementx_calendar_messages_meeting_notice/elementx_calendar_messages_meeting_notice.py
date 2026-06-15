from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import (
    CalendarEventAsset,
    ContactAsset,
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    SmsMessageAsset,
)
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


def utc_ms(year: int, month: int, day: int, hour: int, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


ROOM_ALIAS = "w5-row238-meeting-room"
PINNED_MESSAGE = "Meeting at 2 PM on October 2"
SMS_TEXT = "I have a meeting at 2 PM on October 2, so I cannot attend the dinner."


class ElementXCalendarMessagesMeetingNoticeTask(BaseTask):
    apps = {"ElementX", "Calendar", "Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"

    existing_member = ElementXUserAsset(
        username="w5-row238-existing-member",
        password="password",
        display_name="Existing Planning Member",
    )
    alex_parker = ElementXUserAsset(username="alex-parker", password="password", display_name="Alex Parker")
    noah_brooks = ElementXUserAsset(username="noah-brooks", password="password", display_name="Noah Brooks")
    before_room = ElementXRoomAsset(
        name="Planning Room Original",
        room_type="group",
        creator_username="testuser",
        creator_password="testpass123",
        members=["w5-row238-existing-member"],
        alias_localpart=ROOM_ALIAS,
        topic="Old planning room topic",
    )
    after_room = ElementXRoomAsset(
        name="Meeting Room 1",
        room_type="group",
        creator_username="testuser",
        creator_password="testpass123",
        members=["w5-row238-existing-member", "alex-parker", "noah-brooks"],
        alias_localpart=ROOM_ALIAS,
        topic="Project Task Assignment",
    )
    calendar_event = CalendarEventAsset(
        title="Project Task Assignment Meeting",
        start_ms=utc_ms(2026, 10, 2, 14, 0),
        end_ms=utc_ms(2026, 10, 2, 16, 0),
        location="Online",
        timezone="UTC",
    )
    contact = ContactAsset(name="Henry Hayes", phone_number="+15552012380")
    expected_sms = SmsMessageAsset(
        address=contact.phone_number,
        body=SMS_TEXT,
        box="sent",
        read=True,
    )
    assets = (existing_member, alex_parker, noah_brooks, before_room, contact)

    goal = (
        "Open ElementX and update the room \"Planning Room Original\": rename it to \"Meeting Room 1\", "
        "set the topic to \"Project Task Assignment\", invite Alex Parker and Noah Brooks, send exactly "
        f"\"{PINNED_MESSAGE}\", and pin that message. Then open Calendar and create an event titled "
        "\"Project Task Assignment Meeting\" at Online on October 2, 2026 from 2:00 PM to 4:00 PM. "
        f"Finally open Messages and send Henry Hayes exactly \"{SMS_TEXT}\"."
    )

    def criteria(self):
        return [
            AssetModified(self.before_room, self.after_room, task=self),
            AssetExists(
                ElementXMessageAsset(
                    room=ROOM_ALIAS,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text=PINNED_MESSAGE,
                    pinned=True,
                ),
                task=self,
            ),
            AssetExists(self.calendar_event, task=self),
            AssetExists(self.expected_sms, task=self),
        ]
