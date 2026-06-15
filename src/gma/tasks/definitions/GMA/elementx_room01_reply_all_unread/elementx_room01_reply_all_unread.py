from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ROOM01_ALIAS = "elementx-room01-reply-all-unread-room01"
ROOM02_ALIAS = "elementx-room01-reply-all-unread-room02"
ROOM01_CREATED_AT_MS = 202610011010
ROOM02_CREATED_AT_MS = 202610011020
ROOM01_MESSAGE_CREATED_AT_MS = 202610011030
ROOM02_MESSAGE_CREATED_AT_MS = 202610011040
MESSAGE_TEXT = "How are you today"
REPLY_TEXT = "Received."
ROOM01_UNREAD_TEXT = "Please reply to this Room01 update."
ROOM02_UNREAD_TEXT = "Please reply to this Room02 update."


class ElementXRoom01ReplyAllUnreadTask(BaseTask):
    apps = {"ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    room01_sender = ElementXUserAsset(
        username="room01-unread-alex",
        password="password",
        display_name="Alex Room01",
    )
    room02_sender = ElementXUserAsset(
        username="room02-unread-blair",
        password="password",
        display_name="Blair Room02",
    )
    room01 = ElementXRoomAsset(
        name="Room01",
        room_type="group",
        creator_username="testuser",
        creator_password="testpass123",
        members=["room01-unread-alex"],
        alias_localpart=ROOM01_ALIAS,
        topic="Room01 unread messages",
        created_at_ms=ROOM01_CREATED_AT_MS,
    )
    room02 = ElementXRoomAsset(
        name="Room02",
        room_type="group",
        creator_username="testuser",
        creator_password="testpass123",
        members=["room02-unread-blair"],
        alias_localpart=ROOM02_ALIAS,
        topic="Room02 unread messages",
        created_at_ms=ROOM02_CREATED_AT_MS,
    )
    incoming_room01 = ElementXMessageAsset(
        room=ROOM01_ALIAS,
        sender_username="room01-unread-alex",
        sender_password="password",
        text=ROOM01_UNREAD_TEXT,
        created_at_ms=ROOM01_MESSAGE_CREATED_AT_MS,
    )
    incoming_room02 = ElementXMessageAsset(
        room=ROOM02_ALIAS,
        sender_username="room02-unread-blair",
        sender_password="password",
        text=ROOM02_UNREAD_TEXT,
        created_at_ms=ROOM02_MESSAGE_CREATED_AT_MS,
    )
    expected_room01_message = ElementXMessageAsset(
        room=ROOM01_ALIAS,
        sender_username="testuser",
        sender_password="testpass123",
        text=MESSAGE_TEXT,
    )
    expected_room01_reply = ElementXMessageAsset(
        room=ROOM01_ALIAS,
        sender_username="testuser",
        sender_password="testpass123",
        text=REPLY_TEXT,
        reply_to_text=ROOM01_UNREAD_TEXT,
        reply_to_sender_username="room01-unread-alex",
    )
    expected_room02_reply = ElementXMessageAsset(
        room=ROOM02_ALIAS,
        sender_username="testuser",
        sender_password="testpass123",
        text=REPLY_TEXT,
        reply_to_text=ROOM02_UNREAD_TEXT,
        reply_to_sender_username="room02-unread-blair",
    )
    assets = (
        room01_sender,
        room02_sender,
        room01,
        room02,
        incoming_room01,
        incoming_room02,
        ElementXSessionAsset(username="testuser", password="testpass123"),
    )
    user_interaction = (
        "If the agent asks which room to use for the message, answer exactly: Room01. "
        "Do not answer unrelated questions."
    )
    goal = (
        "Open ElementX, send exactly \"How are you today\" to the room mentioned just now. "
        "Then reply to each unread message with exactly \"Received.\""
    )

    def criteria(self):
        return [
            AssetExists(self.expected_room01_message, task=self),
            AssetExists(self.expected_room01_reply, task=self),
            AssetExists(self.expected_room02_reply, task=self),
        ]
