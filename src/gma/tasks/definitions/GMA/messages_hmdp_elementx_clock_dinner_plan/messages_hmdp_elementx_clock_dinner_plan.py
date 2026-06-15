from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import (
    AlarmAsset,
    ContactAsset,
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    HmdpShopFavoriteAsset,
    HmdpUserAsset,
    SmsMessageAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


REPLY_TEXT = "I've seen it. I'll bookmark the store first, then send the time to the group."
GROUP_MESSAGE = "We'll leave for dinner this Saturday at 4 PM. Everyone, please remember."
SHOP_NAME = "Maple Leaf Bar"
ROOM_ALIAS = "w5-row239-happy-home"


class MessagesHmdpElementXClockDinnerPlanTask(BaseTask):
    apps = {"Messages", "HMDP", "ElementX", "Clock"}
    difficulty = "hard"
    snapshot = "gma_ready_state"

    contact = ContactAsset(name="Casey Chen", phone_number="+15552012390")
    incoming = SmsMessageAsset(
        address=contact.phone_number,
        body="Can you handle the dinner store and tell the group the departure time?",
        box="inbox",
        read=False,
    )
    expected_reply = SmsMessageAsset(
        address=contact.phone_number,
        body=REPLY_TEXT,
        box="sent",
        read=True,
    )
    hmdp_user = HmdpUserAsset(
        phone=HMDP_LOGIN_PHONE,
        password=HMDP_LOGIN_PASSWORD,
        nick_name=HMDP_LOGIN_NICKNAME,
        city="Austin",
        level=1,
    )
    expected_favorite = HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=SHOP_NAME)
    family_member = ElementXUserAsset(
        username="w5-row239-family-member",
        password="password",
        display_name="Happy Home Member",
    )
    room = ElementXRoomAsset(
        name="Happy Home",
        room_type="group",
        creator_username="testuser",
        creator_password="testpass123",
        members=["w5-row239-family-member"],
        alias_localpart=ROOM_ALIAS,
        topic="Family dinner plans",
    )
    expected_alarm = AlarmAsset(hour=15, minute=45, enabled=True, days_of_week=("saturday",))
    assets = (contact, incoming, hmdp_user, family_member, room)

    goal = (
        f"Open Messages and send Casey Chen exactly \"{REPLY_TEXT}\". Then open HMDP, find "
        f"\"{SHOP_NAME}\", and favorite it. Open ElementX, go to the \"Happy Home\" room, and send exactly "
        f"\"{GROUP_MESSAGE}\". Finally open Clock and set an enabled alarm for Saturday at 3:45 PM."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_reply, task=self),
            AssetExists(self.expected_favorite, task=self),
            AssetExists(
                ElementXMessageAsset(
                    room=ROOM_ALIAS,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text=GROUP_MESSAGE,
                ),
                task=self,
            ),
            AssetExists(self.expected_alarm, task=self),
        ]
