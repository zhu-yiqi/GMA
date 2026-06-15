
from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import DeviceFileAsset, ElementXFileAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


FIRST_USER = "w2-row123-avery"
SECOND_USER = "w2-row123-blake"
SECOND_ROOM = elementx_user_id(SECOND_USER)
PROPOSAL_TEXT = "Proposal 1: update the launch checklist before Friday.\n"


class ElementXSecondPrivateChatProposalPinTask(BaseTask):
    apps = {"ElementX", "Files"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    first_user = ElementXUserAsset(username=FIRST_USER, password="password", display_name="Avery Stone")
    second_user = ElementXUserAsset(username=SECOND_USER, password="password", display_name="Blake Fox")
    first_dm = ElementXRoomAsset(name="Avery Stone", room_type="dm", creator_username="testuser", creator_password="testpass123", members=[FIRST_USER], created_at_ms=202610011000)
    second_dm = ElementXRoomAsset(name="Blake Fox", room_type="dm", creator_username="testuser", creator_password="testpass123", members=[SECOND_USER], created_at_ms=202610011010)
    file_asset = DeviceFileAsset(app="Files", storage_dir="Download", filename="proposal1.txt", mime_type="text/plain", text_content=PROPOSAL_TEXT)
    expected_message = ElementXMessageAsset(room=SECOND_ROOM, sender_username="testuser", sender_password="testpass123", text="Please review the new proposal,", pinned=True)
    expected_file = ElementXFileAsset(room=SECOND_ROOM, sender_username="testuser", sender_password="testpass123", filename="proposal1.txt", mime_type="text/plain", text_content=PROPOSAL_TEXT)
    assets = (first_user, second_user, first_dm, second_dm, file_asset, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        "Open ElementX and open the private chat with Blake Fox. "
        "Send the message exactly \"Please review the new proposal,\" and upload the file \"proposal1.txt\". "
        "Pin the message."
    )

    def criteria(self):
        return [AssetExists(self.expected_message, task=self), AssetExists(self.expected_file, task=self)]
