from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import (
    CalendarEventAsset,
    DeviceFileAsset,
    ElementXFileAsset,
    ElementXMessageAsset,
    ElementXPollAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
)
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


def utc_ms(year: int, month: int, day: int, hour: int, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


ROOM_NAME = "A Three-Person Team"
ROOM_ALIAS = "w5-row234-three-person-team"
MESSAGE_TEXT = "Alex Parker's birthday is on October 6. Where should we have dinner?"
POLL_TITLE = "Birthday Dinner Location Options"
VOICE_FILENAME = "birthday-vote-reminder.wav"
VOICE_B64 = "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="


class CalendarElementXBirthdayDinnerPollTask(BaseTask):
    apps = {"Calendar", "ElementX", "Files"}
    difficulty = "hard"
    snapshot = "gma_ready_state"

    old_event = CalendarEventAsset(
        title="September Planning Checkpoint",
        start_ms=utc_ms(2026, 9, 30, 10, 0),
        end_ms=utc_ms(2026, 9, 30, 11, 0),
        description="Seeded event that should be deleted.",
        location="Team Room",
        timezone="UTC",
    )
    birthday_event = CalendarEventAsset(
        title="Alex Parker's Birthday",
        start_ms=utc_ms(2026, 10, 6, 9, 30),
        end_ms=utc_ms(2026, 10, 6, 10, 30),
        description="Remember to bring a birthday gift",
        timezone="UTC",
        reminder_minutes=(0,),
    )
    teammate_one = ElementXUserAsset(
        username="w5-row234-teammate-one",
        password="password",
        display_name="Birthday Teammate One",
    )
    teammate_two = ElementXUserAsset(
        username="w5-row234-teammate-two",
        password="password",
        display_name="Birthday Teammate Two",
    )
    room = ElementXRoomAsset(
        name=ROOM_NAME,
        room_type="group",
        creator_username="testuser",
        creator_password="testpass123",
        members=["w5-row234-teammate-one", "w5-row234-teammate-two"],
        alias_localpart=ROOM_ALIAS,
        topic="Birthday dinner planning",
    )
    voice_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename=VOICE_FILENAME,
        mime_type="audio/wav",
        content_b64=VOICE_B64,
    )
    expected_voice = ElementXFileAsset(
        room=ROOM_ALIAS,
        sender_username="testuser",
        sender_password="testpass123",
        filename=VOICE_FILENAME,
        mime_type="audio/wav",
        content_b64=VOICE_B64,
        pinned=True,
    )
    assets = (old_event, teammate_one, teammate_two, room, voice_file)

    goal = (
        "Open Calendar and delete the event titled \"September Planning Checkpoint\" on September 30, 2026. "
        "Then create a calendar item for October 6, 2026 from 9:30 AM to 10:30 AM titled \"Alex Parker's Birthday\" "
        "with description \"Remember to bring a birthday gift\" and an at-start reminder. "
        f"Next open ElementX, go to \"{ROOM_NAME}\", send exactly \"{MESSAGE_TEXT}\", "
        f"create a poll titled \"{POLL_TITLE}\" with options \"Western Restaurant\" and \"Hunan Restaurant\", "
        f"upload the audio file \"{VOICE_FILENAME}\" from Downloads as the voice reminder, and pin that audio file."
    )

    def criteria(self):
        return [
            AssetDeleted(self.old_event, task=self),
            AssetExists(self.birthday_event, task=self),
            AssetExists(
                ElementXMessageAsset(
                    room=ROOM_ALIAS,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text=MESSAGE_TEXT,
                ),
                task=self,
            ),
            AssetExists(
                ElementXPollAsset(
                    room=ROOM_ALIAS,
                    sender_username="testuser",
                    sender_password="testpass123",
                    question=POLL_TITLE,
                    options=["Western Restaurant", "Hunan Restaurant"],
                ),
                task=self,
            ),
            AssetExists(self.expected_voice, task=self),
        ]
