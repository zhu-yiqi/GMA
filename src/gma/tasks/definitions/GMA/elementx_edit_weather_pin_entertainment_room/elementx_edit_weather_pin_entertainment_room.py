
from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


FIRST_ALIAS = "w2-row130-first-room"
ENT_ALIAS = "w2-row130-entertainment"


class ElementXEditWeatherPinEntertainmentRoomTask(BaseTask):
    apps = {"ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    member = ElementXUserAsset(username="w2-row130-member", password="password", display_name="Avery Reed")
    first_room = ElementXRoomAsset(name="Daily Weather", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row130-member"], alias_localpart=FIRST_ALIAS, topic="Daily chat")
    before_message = ElementXMessageAsset(room=FIRST_ALIAS, sender_username="testuser", sender_password="testpass123", text="The weather is nice today", created_at_ms=202610011000)
    after_message = ElementXMessageAsset(room=FIRST_ALIAS, sender_username="testuser", sender_password="testpass123", text="The weather is bad today")
    expected_pin = ElementXMessageAsset(room=FIRST_ALIAS, sender_username="testuser", sender_password="testpass123", text="I'm exhausted", pinned=True)
    expected_room = ElementXRoomAsset(name="Entertainment", room_type="group", creator_username="testuser", creator_password="testpass123", members=[], alias_localpart=ENT_ALIAS)
    assets = (member, first_room, before_message, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        "Open ElementX, select the first chat room, edit the previously sent message \"The weather is nice today\" to exactly \"The weather is bad today\". "
        "Then send exactly \"I'm exhausted\" and pin it. After that, create a new group chat room named exactly \"Entertainment\"."
    )

    def criteria(self):
        return [AssetModified(self.before_message, self.after_message, task=self), AssetExists(self.expected_pin, task=self), AssetExists(self.expected_room, task=self)]
