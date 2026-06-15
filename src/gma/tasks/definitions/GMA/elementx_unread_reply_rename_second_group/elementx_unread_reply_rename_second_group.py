
from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


FIRST_ALIAS = "w2-row124-first-group"
SECOND_ALIAS = "w2-row124-second-group"
FIRST_ROOM_CREATED_AT_MS = 202610011020
SECOND_ROOM_CREATED_AT_MS = 202610011010
FIRST_MESSAGE_CREATED_AT_MS = 202610011040
SECOND_MESSAGE_CREATED_AT_MS = 202610011030


class ElementXUnreadReplyRenameSecondGroupTask(BaseTask):
    apps = {"ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    user_a = ElementXUserAsset(username="w2-row124-avery", password="password", display_name="Avery")
    user_b = ElementXUserAsset(username="w2-row124-blair", password="password", display_name="Blair")
    first_room = ElementXRoomAsset(name="Daily Updates", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row124-avery"], alias_localpart=FIRST_ALIAS, topic="Updates", created_at_ms=FIRST_ROOM_CREATED_AT_MS)
    second_before = ElementXRoomAsset(name="Old Finds Room", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row124-blair"], alias_localpart=SECOND_ALIAS, topic="Old finds", created_at_ms=SECOND_ROOM_CREATED_AT_MS)
    second_after = ElementXRoomAsset(name="zxc", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row124-blair"], alias_localpart=SECOND_ALIAS, topic="Good Finds Sharing", created_at_ms=SECOND_ROOM_CREATED_AT_MS)
    incoming_one = ElementXMessageAsset(room=FIRST_ALIAS, sender_username="w2-row124-avery", sender_password="password", text="Please acknowledge this update.", created_at_ms=FIRST_MESSAGE_CREATED_AT_MS)
    incoming_two = ElementXMessageAsset(room=SECOND_ALIAS, sender_username="w2-row124-blair", sender_password="password", text="Please acknowledge the finds note.", created_at_ms=SECOND_MESSAGE_CREATED_AT_MS)
    expected_reply_one = ElementXMessageAsset(room=FIRST_ALIAS, sender_username="testuser", sender_password="testpass123", text="Received", reply_to_text="Please acknowledge this update.", reply_to_sender_username="w2-row124-avery")
    expected_reply_two = ElementXMessageAsset(room=SECOND_ALIAS, sender_username="testuser", sender_password="testpass123", text="Received", reply_to_text="Please acknowledge the finds note.", reply_to_sender_username="w2-row124-blair")
    assets = (user_a, user_b, first_room, second_before, incoming_one, incoming_two, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        "Open ElementX and check whether there are unread messages. If there are unread messages, reply to each unread message with exactly \"Received\". "
        "Then rename the group chat room currently named \"Old Finds Room\" exactly to \"zxc\" and set its topic exactly to \"Good Finds Sharing\"."
    )

    def criteria(self):
        return [AssetExists(self.expected_reply_one, task=self), AssetExists(self.expected_reply_two, task=self), AssetModified(self.second_before, self.second_after, task=self)]
