
from __future__ import annotations

from gma.assets import MastodonAccountAsset, MastodonFollowAsset, MastodonSessionAsset, MastodonStatusAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
LATEST_OWNER_POST = "Posting the project summary before the afternoon review."
LATEST_COMMENT = "This summary is useful for the rest of the team."
JACK_POST = "Trying a new planning routine before class."


class MastodonReplyLatestCommentFollowJackSupportTask(BaseTask):
    apps = {"Mastodon"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    jack = MastodonAccountAsset(username="jack", email="jack@example.com", display_name="Jack", bio="Seeded Jack account for follow and comment tasks.")
    commenter = MastodonAccountAsset(username="w2_row101_nina", email="w2.row101.nina@example.com", display_name="Nina Support", bio="Seeded commenter.")
    owner_older_post = MastodonStatusAsset(username=MAIN_USER, text="Finished archiving yesterday's planning notes.", visibility="public", created_at_ms=202609301000)
    owner_latest_post = MastodonStatusAsset(username=MAIN_USER, text=LATEST_OWNER_POST, visibility="public", created_at_ms=202610011000)
    older_comment = MastodonStatusAsset(username="jack", text="I will read the full summary later.", visibility="public", reply_to_username=MAIN_USER, reply_to_text=LATEST_OWNER_POST, created_at_ms=202610011030)
    newest_comment = MastodonStatusAsset(username="w2_row101_nina", text=LATEST_COMMENT, visibility="public", reply_to_username=MAIN_USER, reply_to_text=LATEST_OWNER_POST, created_at_ms=202610011100)
    jack_latest_post = MastodonStatusAsset(username="jack", text=JACK_POST, visibility="public", created_at_ms=202610011115)
    expected_reply = MastodonStatusAsset(username=MAIN_USER, text="Thanks for your support.", visibility="public", reply_to_username="w2_row101_nina", reply_to_text=LATEST_COMMENT)
    expected_follow = MastodonFollowAsset(follower_username=MAIN_USER, followed_username="jack")
    expected_jack_comment = MastodonStatusAsset(username=MAIN_USER, text="Support.", visibility="public", reply_to_username="jack", reply_to_text=JACK_POST)
    assets = (jack, commenter, owner_older_post, owner_latest_post, older_comment, newest_comment, jack_latest_post, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon and reply to the latest comment on your most recent post with exactly "
        "\"Thanks for your support.\" Then search for the user \"Jack\", follow Jack, and if Jack's latest post "
        "has no comments yet, comment exactly \"Support.\" on it."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_reply, task=self),
            AssetExists(self.expected_follow, task=self),
            AssetExists(self.expected_jack_comment, task=self),
        ]
