
from __future__ import annotations

from gma.assets import DeviceFileAsset, ElementXFileAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset
from gma.evaluation import Any, AssetExists
from gma.tasks.base import BaseTask


HAPPY_ALIAS = "w2-row126-happy-sharing"
WORK_ALIAS = "w2-row126-work"
EMILY_PARKER = "w2-row126-emily-parker"
JACK = "jack"
WORK_MEMBER = "w2-row126-workmate"
TASK_TEXT = "Task attachment: finalize the weekly assignment list.\n"


class ElementXHappySharingFallbackInviteWorkFileTask(BaseTask):
    apps = {"ElementX", "Files"}
    difficulty = "medium"
    category = ['Invalid-Instruction Tasks']
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent asks what to do because Ethan Carter is not available in Happy Sharing, answer exactly: Mention Emily Parker instead. Do not answer unrelated questions."
    )

    emily_parker = ElementXUserAsset(username=EMILY_PARKER, password="password", display_name="Emily Parker")
    jack = ElementXUserAsset(username=JACK, password="password", display_name="Jack")
    work_member = ElementXUserAsset(username=WORK_MEMBER, password="password", display_name="Work Mate")
    happy_before = ElementXRoomAsset(name="Happy Sharing", room_type="group", creator_username="testuser", creator_password="testpass123", members=[EMILY_PARKER], alias_localpart=HAPPY_ALIAS, topic="Happy sharing")
    happy_after = ElementXRoomAsset(name="Happy Sharing", room_type="group", creator_username="testuser", creator_password="testpass123", members=[EMILY_PARKER, JACK], alias_localpart=HAPPY_ALIAS, topic="Happy sharing")
    work_room = ElementXRoomAsset(name="Work", room_type="group", creator_username="testuser", creator_password="testpass123", members=[WORK_MEMBER], alias_localpart=WORK_ALIAS, topic="Work files")
    source_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="task.txt", mime_type="text/plain", text_content=TASK_TEXT)
    expected_message = ElementXMessageAsset(room=HAPPY_ALIAS, sender_username="testuser", sender_password="testpass123", text="Please check this update, @Emily Parker.", pinned=True)
    expected_matrix_mention_message = ElementXMessageAsset(room=HAPPY_ALIAS, sender_username="testuser", sender_password="testpass123", text=f"Please check this update, @{EMILY_PARKER}.", pinned=True)
    expected_file = ElementXFileAsset(room=WORK_ALIAS, sender_username="testuser", sender_password="testpass123", filename="task.txt", mime_type="text/plain", text_content=TASK_TEXT)
    assets = (emily_parker, jack, work_member, happy_before, work_room, source_file, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        "Open ElementX, go to the \"Happy Sharing\" group chat, send exactly \"Please check this update, @Ethan Carter.\" and pin that message. "
        "Invite Jack to join Happy Sharing. "
        "Go to the \"Work\" group chat and upload the file \"task.txt\"."
    )

    def criteria(self):
        return [
            Any(
                AssetExists(self.expected_message, task=self),
                AssetExists(self.expected_matrix_mention_message, task=self),
            ),
            AssetExists(self.happy_after, task=self),
            AssetExists(self.expected_file, task=self),
        ]
