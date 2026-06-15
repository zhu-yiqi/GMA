
from __future__ import annotations

from gma.assets import DeviceFileAsset, ElementXFileAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


SECOND_ALIAS = "w2-row127-second-room"
THIRD_ALIAS = "w2-row127-third-room"
FILE_TEXT = "Overtime planning notes for Saturday coverage.\n"
FIRST_ROOM_CREATED_AT_MS = 202610011030
SECOND_ROOM_CREATED_AT_MS = 202610011020
THIRD_ROOM_CREATED_AT_MS = 202610011010


class ElementXWeekendOvertimeFileInviteStudyTopicTask(BaseTask):
    apps = {"ElementX", "Files"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    users = (
        ElementXUserAsset(username="w2-row127-first", password="password", display_name="Avery Reed"),
        ElementXUserAsset(username="w2-row127-second", password="password", display_name="Blake Turner"),
        ElementXUserAsset(username="w2-row127-third", password="password", display_name="Casey Morgan"),
        ElementXUserAsset(username="jack", password="password", display_name="Jack"),
    )
    first_room = ElementXRoomAsset(name="Daily Briefing", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row127-first"], alias_localpart="w2-row127-first-room", topic="Daily briefing", created_at_ms=FIRST_ROOM_CREATED_AT_MS)
    second_before = ElementXRoomAsset(name="Study Circle", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row127-second"], alias_localpart=SECOND_ALIAS, topic="Draft discussion", created_at_ms=SECOND_ROOM_CREATED_AT_MS)
    second_after = ElementXRoomAsset(name="Study Circle", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row127-second"], alias_localpart=SECOND_ALIAS, topic="Study check-in", created_at_ms=SECOND_ROOM_CREATED_AT_MS)
    third_before = ElementXRoomAsset(name="Weekend Overtime", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row127-third"], alias_localpart=THIRD_ALIAS, topic="Weekend coverage", created_at_ms=THIRD_ROOM_CREATED_AT_MS)
    third_after = ElementXRoomAsset(name="Weekend Overtime", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row127-third", "jack"], alias_localpart=THIRD_ALIAS, topic="Weekend coverage", created_at_ms=THIRD_ROOM_CREATED_AT_MS)
    source_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="overtime-plan.txt", mime_type="text/plain", text_content=FILE_TEXT)
    expected_message = ElementXMessageAsset(room=THIRD_ALIAS, sender_username="testuser", sender_password="testpass123", text="need to work overtime on Saturday.", pinned=True)
    expected_file = ElementXFileAsset(room=THIRD_ALIAS, sender_username="testuser", sender_password="testpass123", filename="overtime-plan.txt", mime_type="text/plain", text_content=FILE_TEXT)
    assets = (*users, first_room, second_before, third_before, source_file, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        "Open ElementX, select the Weekend Overtime chat room, send exactly \"need to work overtime on Saturday.\", upload \"overtime-plan.txt\", and pin that sent message. "
        "Invite friend Jack to join the Weekend Overtime chat room. Then change the description of the Study Circle chat room exactly to \"Study check-in\"."
    )

    def criteria(self):
        return [AssetExists(self.expected_message, task=self), AssetExists(self.expected_file, task=self), AssetExists(self.third_after, task=self), AssetModified(self.second_before, self.second_after, task=self)]
