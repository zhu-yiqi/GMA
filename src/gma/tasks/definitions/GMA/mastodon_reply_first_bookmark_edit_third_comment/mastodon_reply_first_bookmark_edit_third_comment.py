
from __future__ import annotations

from gma.assets import MastodonBookmarkAsset, MastodonSessionAsset, MastodonStatusAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
FIRST_POST = "First profile post for the reply and bookmark step."
SECOND_POST = "Second profile post left unchanged."
THIRD_BEFORE = "Third profile post before editing."
THIRD_AFTER = "Sharing with everyone"


class MastodonReplyFirstBookmarkEditThirdCommentTask(BaseTask):
    apps = {"Mastodon"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent asks what to write when replying to the first post, answer exactly: "
        "Thanks for sharing. Do not answer unrelated questions."
    )

    first_post = MastodonStatusAsset(username=MAIN_USER, text=FIRST_POST, visibility="public", created_at_ms=202610011200)
    second_post = MastodonStatusAsset(username=MAIN_USER, text=SECOND_POST, visibility="public", created_at_ms=202610011100)
    third_before = MastodonStatusAsset(username=MAIN_USER, text=THIRD_BEFORE, visibility="public", created_at_ms=202610011000)
    third_after = MastodonStatusAsset(username=MAIN_USER, text=THIRD_AFTER, visibility="public")
    expected_reply = MastodonStatusAsset(username=MAIN_USER, text="Thanks for sharing.", visibility="public", reply_to_username=MAIN_USER, reply_to_text=FIRST_POST)
    expected_bookmark = MastodonBookmarkAsset(actor_username=MAIN_USER, target_username=MAIN_USER, target_text=FIRST_POST)
    expected_comment = MastodonStatusAsset(username=MAIN_USER, text="Hope everyone checks in more often!", visibility="public", reply_to_username=MAIN_USER, reply_to_text=THIRD_AFTER)
    assets = (first_post, second_post, third_before, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon, reply to the first post in your profile timeline, and bookmark that first post. "
        "Edit your third profile post so its content is exactly \"Sharing with everyone\". "
        "If no one has commented on that third post, comment exactly \"Hope everyone checks in more often!\" on it."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_reply, task=self),
            AssetExists(self.expected_bookmark, task=self),
            AssetModified(self.third_before, self.third_after, task=self),
            AssetExists(self.expected_comment, task=self),
        ]
