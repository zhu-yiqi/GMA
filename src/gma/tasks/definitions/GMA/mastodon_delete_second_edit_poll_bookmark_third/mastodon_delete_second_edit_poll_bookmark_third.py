
from __future__ import annotations

from gma.assets import MastodonBookmarkAsset, MastodonPollSpec, MastodonPollStatusAsset, MastodonSessionAsset, MastodonStatusAsset
from gma.evaluation import AssetDeleted, AssetExists, AssetModified
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
FIRST_POLL_TEXT = "Which lunch should I choose today?"
FIRST_POLL_TEXT_AFTER = "Which lunch should I choose today or like both?"
SECOND_POST_TEXT = "Second timeline note for cleanup."
THIRD_POST_TEXT = "Third timeline note for the bookmark branch."


class MastodonDeleteSecondEditPollBookmarkThirdTask(BaseTask):
    apps = {"Mastodon"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    first_poll_before = MastodonPollStatusAsset(
        username=MAIN_USER,
        text=FIRST_POLL_TEXT,
        visibility="public",
        poll=MastodonPollSpec(options=("French fries trio", "Mai la Ji tui Bao single meal"), multiple=False),
        created_at_ms=202610011100,
    )
    second_post = MastodonStatusAsset(username=MAIN_USER, text=SECOND_POST_TEXT, visibility="public", created_at_ms=202610011000)
    third_post = MastodonStatusAsset(username=MAIN_USER, text=THIRD_POST_TEXT, visibility="public", created_at_ms=202610010900)
    first_poll_after = MastodonPollStatusAsset(
        username=MAIN_USER,
        text=FIRST_POLL_TEXT_AFTER,
        visibility="public",
        poll=MastodonPollSpec(options=("French fries trio", "Mai la Ji tui Bao single meal", "1 and 2"), multiple=False),
    )
    expected_bookmark = MastodonBookmarkAsset(actor_username=MAIN_USER, target_username=MAIN_USER, target_text=THIRD_POST_TEXT)
    assets = (first_poll_before, second_post, third_post, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon. Delete your second profile post. Edit your first poll post by inserting "
        "\"or like both\" immediately before the question mark and adding a new poll option exactly \"1 and 2\". "
        "Then check your third profile post: if it is already bookmarked, unbookmark it; otherwise bookmark it."
    )

    def criteria(self):
        return [
            AssetDeleted(self.second_post, task=self),
            AssetModified(self.first_poll_before, self.first_poll_after, task=self),
            AssetExists(self.expected_bookmark, task=self),
        ]
