from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import ContactAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, SmsMessageAsset
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


FIRST_SMS = SmsMessageAsset(address="5550101111", body="Please confirm this thread.", box="inbox", read=True, timestamp_ms=202610010900)
TIKTOK = SmsMessageAsset(address="5550101112", body="TikTok verification code: 640219", box="inbox", read=False, timestamp_ms=202610010910)
ROOM_ALIAS = "first_direct_code_room"
CODE_FRIEND_DM = elementx_user_id("codefriend")


class MessagesTikTokCodeToElementXDmTask(BaseTask):
    apps = {"Messages", "ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        ContactAsset(name="First SMS", phone_number="5550101111"),
        ContactAsset(name="TikTok", phone_number="5550101112"),
        FIRST_SMS,
        TIKTOK,
        ElementXUserAsset(username="codefriend", password="password", display_name="Code Friend"),
        ElementXRoomAsset(
            name="First Direct Code Room",
            room_type="dm",
            creator_username="testuser",
            creator_password="testpass123",
            members=["codefriend"],
            alias_localpart=ROOM_ALIAS,
        ),
    )
    goal = (
        "Open Messages, send exactly \"OK\" to the earliest existing SMS conversation, then delete "
        "that SMS conversation. Mark all remaining SMS as read. Read the TikTok verification code, "
        "then open ElementX and send that code to the Code Friend one-on-one chat."
    )

    def criteria(self):
        return [
            AssetDeleted(FIRST_SMS, task=self),
            AssetExists(
                ElementXMessageAsset(
                    room=CODE_FRIEND_DM,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text="640219",
                ),
                task=self,
            ),
        ]
