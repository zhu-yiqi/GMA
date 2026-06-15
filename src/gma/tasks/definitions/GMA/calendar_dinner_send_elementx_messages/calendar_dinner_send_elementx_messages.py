from __future__ import annotations

from gma.assets import CalendarEventAsset, ContactAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, SmsMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask
from datetime import UTC, datetime

from gma.apps.travel import (
    TRAVEL_LOGIN_EMAIL,
    TRAVEL_LOGIN_FIRST_NAME,
    TRAVEL_LOGIN_LAST_NAME,
    TRAVEL_LOGIN_PASSWORD,
    TRAVEL_LOGIN_USERNAME,
    login_travel_app,
)
from gma.assets import TravelUserAsset

TRAVEL_USER = TravelUserAsset(
    email=TRAVEL_LOGIN_EMAIL,
    username=TRAVEL_LOGIN_USERNAME,
    password=TRAVEL_LOGIN_PASSWORD,
    first_name=TRAVEL_LOGIN_FIRST_NAME,
    last_name=TRAVEL_LOGIN_LAST_NAME,
)


def dt_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


def open_travel(client) -> None:
    login_travel_app(
        client,
        email=TRAVEL_LOGIN_EMAIL,
        username=TRAVEL_LOGIN_USERNAME,
        password=TRAVEL_LOGIN_PASSWORD,
        ensure_user=False,
    )

EVENT = CalendarEventAsset(title="Old Friends Dinner", start_ms=dt_ms(2026, 10, 3, 19), end_ms=dt_ms(2026, 10, 3, 20), location="Veteran BBQ Restaurant", timezone="UTC")
SUMMARY = "Old Friends Dinner: October 3, 2026 7:00 PM at Veteran BBQ Restaurant"
ROOM_ALIAS = "w4-row205-first-room"
CONTACT = ContactAsset(name="First Conversation", phone_number="+15550152005")
SEED_SMS = SmsMessageAsset(address=CONTACT.phone_number, body="Please send me the dinner details after you create them.", box="inbox", read=True, timestamp_ms=202610010900)
EXPECTED_REPLY = SmsMessageAsset(address=CONTACT.phone_number, body=SUMMARY, box="sent", read=True)
EXPECTED_ELEMENTX = ElementXMessageAsset(room=ROOM_ALIAS, sender_username="testuser", sender_password="testpass123", text=SUMMARY)


class CalendarDinnerSendElementXMessagesTask(BaseTask):
    apps = {"Calendar", "ElementX", "Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (ElementXUserAsset(username="w4-row205-friend", display_name="Dinner Friend"), ElementXRoomAsset(name="First Dinner Room", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w4-row205-friend"], alias_localpart=ROOM_ALIAS), CONTACT, SEED_SMS)
    goal = (
        'Create a Calendar event titled "Old Friends Dinner" at Veteran BBQ Restaurant for Saturday, October 3, 2026 at 7:00 PM. '
        "Then use that Calendar event's details to send a summary to First Dinner Room in ElementX and to the First Conversation Messages thread. "
        'Use exactly this format: "Old Friends Dinner: <Month day, year time> at <location>".'
    )

    def criteria(self):
        return [AssetExists(EVENT, task=self), AssetExists(EXPECTED_ELEMENTX, task=self), AssetExists(EXPECTED_REPLY, task=self)]
