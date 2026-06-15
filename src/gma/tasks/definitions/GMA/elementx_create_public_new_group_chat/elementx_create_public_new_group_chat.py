from __future__ import annotations

from gma.assets import ElementXRoomAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ROOM_NAME = "New Group Chat"
ROOM_ALIAS = "new-group-chat-w1"
ROOM_TOPIC = "Group Chat"


class ElementXCreatePublicNewGroupChatTask(BaseTask):
    apps = {"ElementX"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    expected_room = ElementXRoomAsset(
        name=ROOM_NAME,
        room_type="group",
        alias_localpart=ROOM_ALIAS,
        topic=ROOM_TOPIC,
    )

    goal = (
        'Open ElementX and create a public group chat named "New Group Chat". '
        'Set its topic exactly to "Group Chat".'
    )

    def criteria(self):
        return [AssetExists(self.expected_room, task=self)]
