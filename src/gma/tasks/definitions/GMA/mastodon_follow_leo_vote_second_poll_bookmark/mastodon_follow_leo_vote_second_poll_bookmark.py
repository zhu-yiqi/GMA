
from __future__ import annotations

from gma.assets import (
    MastodonAccountAsset,
    MastodonFavoriteAsset,
    MastodonFollowAsset,
    MastodonPollSpec,
    MastodonPollStatusAsset,
    MastodonPollVoteAsset,
    MastodonSessionAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
TARGET_USER = "leo"
FIRST_POLL_TEXT = "Which campus snack should I review first?"
SECOND_POLL_TEXT = "Which study break plan should I try tomorrow?"
SECOND_FIRST_OPTION = "Walk outside"


class MastodonFollowLeoVoteSecondPollBookmarkTask(BaseTask):
    apps = {"Mastodon"}
    difficulty = "medium"
    category = []
    snapshot = "gma_ready_state"

    leo = MastodonAccountAsset(username=TARGET_USER, email="leo@example.com", display_name="Leo", bio="Seeded poll account.")
    first_poll = MastodonPollStatusAsset(
        username=TARGET_USER,
        text=FIRST_POLL_TEXT,
        visibility="public",
        poll=MastodonPollSpec(options=("Fruit cup", "Granola bar"), multiple=False),
        created_at_ms=202610011100,
    )
    second_poll = MastodonPollStatusAsset(
        username=TARGET_USER,
        text=SECOND_POLL_TEXT,
        visibility="public",
        poll=MastodonPollSpec(options=(SECOND_FIRST_OPTION, "Stay in the library"), multiple=False),
        created_at_ms=202610011000,
    )
    expected_follow = MastodonFollowAsset(follower_username=MAIN_USER, followed_username=TARGET_USER)
    expected_vote = MastodonPollVoteAsset(voter_username=MAIN_USER, poll_username=TARGET_USER, poll_text=SECOND_POLL_TEXT, choices=(SECOND_FIRST_OPTION,))
    expected_favorite = MastodonFavoriteAsset(actor_username=MAIN_USER, target_username=TARGET_USER, target_text=SECOND_POLL_TEXT)
    assets = (leo, first_poll, second_poll, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon, search for user \"leo\", go to Leo's profile and follow him. "
        "Find Leo's poll post about study break plans, vote for the first option, and favorite that poll post."
    )

    def criteria(self):
        return [AssetExists(self.expected_follow, task=self), AssetExists(self.expected_vote, task=self), AssetExists(self.expected_favorite, task=self)]
