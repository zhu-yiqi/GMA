from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


CONTACT = "jordan-lee"
CONTACT_DISPLAY = "Jordan Lee"
MESSAGE = "Long time no see"
ROOM_REF = elementx_user_id(CONTACT)


class ElementXSendLongTimeNoSeeJordanTask(BaseTask):
    apps = {"ElementX"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    assets = (
        ElementXUserAsset(username=CONTACT, password="password", display_name=CONTACT_DISPLAY),
        ElementXRoomAsset(
            name=CONTACT_DISPLAY,
            room_type="dm",
            creator_username="testuser",
            creator_password="testpass123",
            members=[CONTACT],
        ),
    )
    expected_message = ElementXMessageAsset(
        room=ROOM_REF,
        sender_username="testuser",
        sender_password="testpass123",
        text=MESSAGE,
    )

    goal = 'Open ElementX, find the private chat with Jordan Lee, and send exactly "Long time no see".'

    def criteria(self):
        return [AssetExists(self.expected_message, task=self)]
