from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


CONTACT = "ethan_carter"
CONTACT_DISPLAY = "Ethan Carter"
MESSAGE = "Received!"
ROOM_REF = elementx_user_id(CONTACT)


class ElementXPinReceivedMessageFromEthanTask(BaseTask):
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
        ElementXMessageAsset(
            room=ROOM_REF,
            sender_username=CONTACT,
            sender_password="password",
            text=MESSAGE,
            pinned=False,
        ),
    )

    goal = 'Open ElementX, find the private chat with Ethan Carter, and pin the message "Received!"'

    def criteria(self):
        return [
            AssetModified(
                ElementXMessageAsset(room=ROOM_REF, sender_username=CONTACT, sender_password="password", text=MESSAGE, pinned=False),
                ElementXMessageAsset(room=ROOM_REF, sender_username=CONTACT, sender_password="password", text=MESSAGE, pinned=True),
                task=self,
            )
        ]
