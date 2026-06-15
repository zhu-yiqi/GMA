
from __future__ import annotations

from gma.assets import MastodonAccountAsset, MastodonBookmarkAsset, MastodonPollSpec, MastodonPollStatusAsset, MastodonSessionAsset, MastodonStatusAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
SECOND_POST = "Second post about tomorrow's concert logistics."
SECOND_COMMENT = "Maybe the concert entrance plan should be adjusted."
REPLY_TEXT = "I think your idea is also good."
POLL_TEXT = "Will you attend tomorrow's concert?"


class MastodonConcertPollReplySecondCommentBookmarkTask(BaseTask):
    apps = {"Mastodon"}
    difficulty = "medium"
    category = ['Information-Gathering Tasks', 'Conditional Tasks']
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent asks what to write when replying to the second comment, answer exactly: "
        "I think your idea is also good. Do not answer unrelated questions."
    )

    commenter_a = MastodonAccountAsset(username="w2_row109_commenter_a", email="w2.row109.a@example.com", display_name="Concert A")
    commenter_b = MastodonAccountAsset(username="w2_row109_commenter_b", email="w2.row109.b@example.com", display_name="Concert B")
    first_post = MastodonStatusAsset(username=MAIN_USER, text="First post about the concert poster.", visibility="public", created_at_ms=202610011200)
    second_post = MastodonStatusAsset(username=MAIN_USER, text=SECOND_POST, visibility="public", created_at_ms=202610011100)
    first_comment = MastodonStatusAsset(username="w2_row109_commenter_a", text="I can arrive a little early.", visibility="public", reply_to_username=MAIN_USER, reply_to_text=SECOND_POST, created_at_ms=202610011120)
    second_comment = MastodonStatusAsset(username="w2_row109_commenter_b", text=SECOND_COMMENT, visibility="public", reply_to_username=MAIN_USER, reply_to_text=SECOND_POST, created_at_ms=202610011130)
    expected_poll = MastodonPollStatusAsset(username=MAIN_USER, text=POLL_TEXT, visibility="public", poll=MastodonPollSpec(options=("Yes", "No"), multiple=False))
    expected_reply = MastodonStatusAsset(username=MAIN_USER, text=REPLY_TEXT, visibility="public", reply_to_username="w2_row109_commenter_b", reply_to_text=SECOND_COMMENT)
    expected_bookmark = MastodonBookmarkAsset(actor_username=MAIN_USER, target_username=MAIN_USER, target_text=SECOND_POST)
    assets = (commenter_a, commenter_b, first_post, second_post, first_comment, second_comment, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon and publish a public single-choice poll asking exactly \"Will you attend tomorrow's concert?\" "
        "with options \"Yes\" and \"No\". Then reply to the second comment under your second profile post; "
        "If that second profile post is not already bookmarked, bookmark it."
    )

    def criteria(self):
        return [AssetExists(self.expected_poll, task=self), AssetExists(self.expected_reply, task=self), AssetExists(self.expected_bookmark, task=self)]
