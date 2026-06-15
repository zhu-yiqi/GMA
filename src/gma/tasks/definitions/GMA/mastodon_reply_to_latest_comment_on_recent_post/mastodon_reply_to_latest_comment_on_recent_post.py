from __future__ import annotations

from gma.assets import MastodonAccountAsset, MastodonSessionAsset, MastodonStatusAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
OLDER_POST = "Wrapping up the archive cleanup today."
LATEST_POST = "Shared the release checklist with the team this afternoon."
OLDER_COMMENT = "I can review the checklist before lunch."
LATEST_COMMENT = "The release checklist looks complete from my side."
REPLY_TEXT = "Thank you."


class MastodonReplyToLatestCommentOnRecentPostTask(BaseTask):
    apps = {"Mastodon"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    reviewer = MastodonAccountAsset(
        username="nina_patel",
        email="nina.patel@example.com",
        display_name="Nina Patel",
        bio="Seeded reviewer account for comment-reply tasks.",
    )
    observer = MastodonAccountAsset(
        username="owen_miles",
        email="owen.miles@example.com",
        display_name="Owen Miles",
        bio="Seeded observer account for comment-reply context.",
    )
    older_owner_post = MastodonStatusAsset(
        username=MAIN_USER,
        text=OLDER_POST,
        visibility="public",
        created_at_ms=1790845200000,
    )
    latest_owner_post = MastodonStatusAsset(
        username=MAIN_USER,
        text=LATEST_POST,
        visibility="public",
        created_at_ms=1790845500000,
    )
    older_comment = MastodonStatusAsset(
        username="owen_miles",
        text=OLDER_COMMENT,
        visibility="public",
        reply_to_username=MAIN_USER,
        reply_to_text=LATEST_POST,
        created_at_ms=1790845800000,
    )
    latest_comment = MastodonStatusAsset(
        username="nina_patel",
        text=LATEST_COMMENT,
        visibility="public",
        reply_to_username=MAIN_USER,
        reply_to_text=LATEST_POST,
        created_at_ms=1790846100000,
    )
    expected_reply = MastodonStatusAsset(
        username=MAIN_USER,
        text=REPLY_TEXT,
        visibility="public",
        reply_to_username="nina_patel",
        reply_to_text=LATEST_COMMENT,
    )
    assets = (
        reviewer,
        observer,
        older_owner_post,
        latest_owner_post,
        older_comment,
        latest_comment,
        MastodonSessionAsset(username=MAIN_USER),
    )

    goal = (
        'Open Mastodon, find your post "Shared the release checklist with the team this afternoon.", '
        'and reply to Nina Patel\'s comment "The release checklist looks complete from my side." '
        'with exactly "Thank you."'
    )

    def criteria(self):
        return [AssetExists(self.expected_reply, task=self)]
