from __future__ import annotations

from gma.assets import (
    MastodonAccountAsset,
    MastodonBookmarkAsset,
    MastodonFollowAsset,
    MastodonReblogAsset,
    MastodonSessionAsset,
    MastodonStatusAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
TARGET_USER = "campus_menu"
TARGET_TEXT = "Tonight's campus dinner vote is open."


class MastodonBookmarkAndRepostHomeFirstPostTask(BaseTask):
    apps = {"Mastodon"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    target_account = MastodonAccountAsset(
        username=TARGET_USER,
        email="campus-menu@example.com",
        display_name="Campus Menu",
        bio="Short campus dining updates.",
    )
    target_status = MastodonStatusAsset(
        username=TARGET_USER,
        text=TARGET_TEXT,
        visibility="public",
        created_at_ms=1790809200000,
    )
    older_status = MastodonStatusAsset(
        username=TARGET_USER,
        text="Breakfast specials are posted near the cafeteria door.",
        visibility="public",
        created_at_ms=1790802000000,
    )
    expected_bookmark = MastodonBookmarkAsset(
        actor_username=MAIN_USER,
        target_username=TARGET_USER,
        target_text=TARGET_TEXT,
    )
    expected_reblog = MastodonReblogAsset(
        actor_username=MAIN_USER,
        target_username=TARGET_USER,
        target_text=TARGET_TEXT,
    )
    owner_follow = MastodonFollowAsset(follower_username=MAIN_USER, followed_username=TARGET_USER)
    assets = (target_account, older_status, target_status, owner_follow, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon. On the home timeline, bookmark and then repost the first post, "
        "which says \"Tonight's campus dinner vote is open.\""
    )

    def criteria(self):
        return [
            AssetExists(self.expected_bookmark, task=self),
            AssetExists(self.expected_reblog, task=self),
        ]
