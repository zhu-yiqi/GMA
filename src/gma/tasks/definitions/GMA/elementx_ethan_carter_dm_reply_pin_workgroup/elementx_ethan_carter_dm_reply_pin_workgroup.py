
from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ETHAN_CARTER = "w2-row128-ethan-carter"
DM_ROOM = elementx_user_id(ETHAN_CARTER)
WORK_ALIAS = "w2-row128-work-group-2"
PIN_TEXT = "Meeting at 2 PM"


class ElementXEthanCarterDmReplyPinWorkgroupTask(BaseTask):
    apps = {"ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    ethan_carter = ElementXUserAsset(username=ETHAN_CARTER, password="password", display_name="Ethan Carter")
    work_member = ElementXUserAsset(username="w2-row128-workmate", password="password", display_name="Workmate")
    dm_room = ElementXRoomAsset(name="Ethan Carter", room_type="dm", creator_username="testuser", creator_password="testpass123", members=[ETHAN_CARTER])
    work_room = ElementXRoomAsset(name="Work Group 2", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row128-workmate"], alias_localpart=WORK_ALIAS, topic="Work")
    seed_meeting = ElementXMessageAsset(room=WORK_ALIAS, sender_username="w2-row128-workmate", sender_password="password", text=PIN_TEXT, pinned=False, created_at_ms=202610011000)
    expected_dm_message = ElementXMessageAsset(room=DM_ROOM, sender_username="testuser", sender_password="testpass123", text="Has the document we discussed last time been updated?")
    expected_reply = ElementXMessageAsset(room=DM_ROOM, sender_username="testuser", sender_password="testpass123", text="Especially the parts that are critically mentioned.", reply_to_text="Has the document we discussed last time been updated?", reply_to_sender_username="testuser")
    expected_pin = ElementXMessageAsset(room=WORK_ALIAS, sender_username="w2-row128-workmate", sender_password="password", text=PIN_TEXT, pinned=True)
    assets = (ethan_carter, work_member, dm_room, work_room, seed_meeting, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        "Open ElementX, start or enter the private chat with Ethan Carter, and send exactly \"Has the document we discussed last time been updated?\". "
        "Reply to that sent message with exactly \"Especially the parts that are critically mentioned.\" "
        "Then enter the group chat \"Work Group 2\" and check whether the message \"Meeting at 2 PM\" is pinned; it is not pinned, so pin it."
    )

    def criteria(self):
        return [AssetExists(self.expected_dm_message, task=self), AssetExists(self.expected_reply, task=self), AssetExists(self.expected_pin, task=self)]
