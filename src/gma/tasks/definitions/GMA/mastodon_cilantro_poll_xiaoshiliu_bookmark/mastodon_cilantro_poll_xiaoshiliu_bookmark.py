
from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    MastodonPollSpec,
    MastodonPollStatusAsset,
    MastodonSessionAsset,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuSessionAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
AUTHOR_ID = "w2-row102-cilantro-author"
TARGET_TITLE = "Why Some People Dislike Cilantro"
TARGET_IMAGE = "mastodon-cilantro-poll-xiaoshiliu-bookmark-cilantro-post.png"

class MastodonCilantroPollXiaoShiLiuBookmarkTask(BaseTask):
    apps = {"Mastodon", "XiaoShiLiu"}
    difficulty = "medium"
    category = ['Information-Gathering Tasks']
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent asks what options to use for the cilantro poll, answer exactly: "
        "Use options \"Yes\" and \"No\". Do not answer unrelated questions."
    )

    author = XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Cilantro Notes", email="cilantro.notes@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR, bio="Short campus food science notes.", location="Seed Campus")
    target_post = XiaoShiLiuPostAsset(
        author_user_id=AUTHOR_ID,
        title=TARGET_TITLE,
        content="Why do some people dislike cilantro? A quick note about aroma, genetics, and food memories.",
        category="Food",
        image_urls=[f"/assets/{TARGET_IMAGE}"],
        min_image_count=1,
        created_at_ms=202610011000,
    )
    distractor_post = XiaoShiLiuPostAsset(
        author_user_id=AUTHOR_ID,
        title="Campus Herb Garden Update",
        content="A short note about basil and mint near the cafeteria planters.",
        category="Food",
        image_urls=[f"/assets/{TARGET_IMAGE}"],
        min_image_count=1,
        created_at_ms=202609301000,
    )
    expected_poll = MastodonPollStatusAsset(
        username=MAIN_USER,
        text="Do you like cilantro?",
        visibility="public",
        poll=MastodonPollSpec(options=("Yes", "No"), multiple=False),
    )
    expected_collection = XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=TARGET_TITLE, post_author_user_id=AUTHOR_ID)
    assets = (MastodonSessionAsset(username=MAIN_USER), XiaoShiLiuSessionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID), author, distractor_post, target_post)

    goal = (
        "Open Mastodon and publish a public single-choice poll with exactly \"Do you like cilantro?\" as the question. "
        "Then open XiaoShiLiu, search exactly \"Why do some people dislike cilantro\", "
        "and bookmark the first result."
    )

    def criteria(self):
        return [AssetExists(self.expected_poll, task=self), AssetExists(self.expected_collection, task=self)]
