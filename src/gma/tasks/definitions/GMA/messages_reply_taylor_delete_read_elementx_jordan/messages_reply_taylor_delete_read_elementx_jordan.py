from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import ContactAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, SmsMessageAsset
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


TAYLOR_INBOX = SmsMessageAsset(address="5550101108", body="Please review the delivery result.", box="inbox", read=True, timestamp_ms=202610010900)
TAYLOR_REPLY = SmsMessageAsset(address="5550101108", body="Received", box="sent", read=True)
READ_ONE = SmsMessageAsset(address="5550101109", body="Read archive one.", box="inbox", read=True, timestamp_ms=202610010910)
READ_TWO = SmsMessageAsset(address="5550101110", body="Read archive two.", box="inbox", read=True, timestamp_ms=202610010920)
ROOM_ALIAS = "jordan_dinner_chat"
JORDAN_DM = elementx_user_id("jordan-lee")
ELEMENTX_MESSAGE = "I just received Taylor's message. Do you want to know the result?"


class MessagesReplyTaylorDeleteReadElementXJordanTask(BaseTask):
    apps = {"Messages", "ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        ContactAsset(name="Taylor", phone_number="5550101108"),
        ContactAsset(name="Dana Scott", phone_number="5550101109"),
        ContactAsset(name="Logan Price", phone_number="5550101110"),
        TAYLOR_INBOX,
        READ_ONE,
        READ_TWO,
        ElementXUserAsset(username="jordan-lee", password="password", display_name="Jordan Lee"),
        ElementXRoomAsset(
            name="Jordan Lee dinner chat",
            room_type="dm",
            creator_username="testuser",
            creator_password="testpass123",
            members=["jordan-lee"],
            alias_localpart=ROOM_ALIAS,
            topic="Dinner-result direct chat.",
        ),
    )
    goal = (
        "Open Messages and send Taylor exactly \"Received\". Then delete the two read SMS "
        "conversations named Dana Scott and Logan Price. Open ElementX and send Jordan Lee "
        "exactly this message: \"I just received Taylor's message. Do you want to know the result?\""
    )

    def criteria(self):
        return [
            AssetExists(TAYLOR_REPLY, task=self),
            AssetDeleted(READ_ONE, task=self),
            AssetDeleted(READ_TWO, task=self),
            AssetExists(
                ElementXMessageAsset(
                    room=JORDAN_DM,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text=ELEMENTX_MESSAGE,
                ),
                task=self,
            ),
        ]
