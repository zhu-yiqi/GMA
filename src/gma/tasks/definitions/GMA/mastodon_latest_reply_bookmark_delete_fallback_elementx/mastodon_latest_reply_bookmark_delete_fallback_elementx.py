
from __future__ import annotations

from gma.assets import (
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXSessionAsset,
    ElementXUserAsset,
    MastodonAccountAsset,
    MastodonBookmarkAsset,
    MastodonSessionAsset,
    MastodonStatusAsset,
)
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
EXTERNAL_USER = "daily_notes"
LATEST_POST = "Today's campus update is ready for review."
ONLY_OWNER_POST = "Only owner post available for the deletion fallback."
ROOM_NAME = "Morning Crew"


class MastodonLatestReplyBookmarkDeleteFallbackElementXTask(BaseTask):
    apps = {"Mastodon", "ElementX"}
    difficulty = "medium"
    category = ['Invalid-Instruction Tasks']
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent says it cannot find your second Mastodon post and asks what to do, "
        "answer exactly: Then delete my first post instead. Do not answer unrelated questions."
    )

    external_account = MastodonAccountAsset(username=EXTERNAL_USER, email="daily.notes@example.com", display_name="Daily Notes", bio="Campus update account.")
    external_latest_post = MastodonStatusAsset(username=EXTERNAL_USER, text=LATEST_POST, visibility="public", created_at_ms=202610011200)
    owner_only_post = MastodonStatusAsset(username=MAIN_USER, text=ONLY_OWNER_POST, visibility="public", created_at_ms=202610011000)
    member = ElementXUserAsset(username="w2-row104-sam", password="password", display_name="Sam Green")
    group_room = ElementXRoomAsset(name=ROOM_NAME, room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row104-sam"], created_at_ms=202610011010)
    expected_reply = MastodonStatusAsset(username=MAIN_USER, text="The content today is also great!", visibility="public", reply_to_username=EXTERNAL_USER, reply_to_text=LATEST_POST)
    expected_bookmark = MastodonBookmarkAsset(actor_username=MAIN_USER, target_username=EXTERNAL_USER, target_text=LATEST_POST)
    expected_elementx_message = ElementXMessageAsset(room=ROOM_NAME, sender_username="testuser", sender_password="testpass123", text="Good morning!")
    assets = (external_account, external_latest_post, owner_only_post, MastodonSessionAsset(username=MAIN_USER), member, group_room, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        "Open Mastodon and delete your second profile post. "
        "Then search for user \"Daily Notes\", find the post \"Today's campus update is ready for review.\", "
        "reply to that post with exactly \"The content today is also great!\", and bookmark that post. "
        "Open ElementX and send exactly \"Good morning!\" "
        "to the first group chat."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_reply, task=self),
            AssetExists(self.expected_bookmark, task=self),
            AssetDeleted(self.owner_only_post, task=self),
            AssetExists(self.expected_elementx_message, task=self),
        ]
