from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    XiaoShiLiuCommentAsset,
    XiaoShiLiuFollowAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


FOODIE_USER = "foodie-carter"
GUITAR_USER = "guitar-mentor"
LATEST_POST = XiaoShiLiuPostAsset(
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    title="Morning Coffee Snapshot",
    content="A quiet coffee before class.",
    category="Campus Life",
    tags=["morning"],
    image_urls=["/assets/002-latest-coffee-post.png"],
    min_image_count=1,
    created_at_ms=1790846400000,
)
REMAINING_FIRST_POST = XiaoShiLiuPostAsset(
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    title="Library Walk Notes",
    content="A calm walk through the library hall.",
    category="Study",
    tags=["study"],
    image_urls=["/assets/003-second-food-post.png"],
    min_image_count=1,
    created_at_ms=1790846100000,
)
TARGET_SECOND_POST = XiaoShiLiuPostAsset(
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    title="Simple Lunch Bowl",
    content="A simple lunch bowl after practice.",
    category="Food",
    tags=["food"],
    image_urls=["/assets/003-second-food-post.png"],
    min_image_count=1,
    created_at_ms=1790845500000,
)
FOODIE_COMMENT = XiaoShiLiuCommentAsset(
    post_title="Simple Lunch Bowl",
    post_author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    author_user_id=FOODIE_USER,
    content="Try the lemon sauce first.",
    created_at_ms=1790845800000,
)
EXPECTED_REPLY = XiaoShiLiuCommentAsset(
    post_title="Simple Lunch Bowl",
    post_author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    content="hh",
    parent_content="Try the lemon sauce first.",
    parent_author_user_id=FOODIE_USER,
)
GUITAR_POST = XiaoShiLiuPostAsset(
    author_user_id=GUITAR_USER,
    title="Learning Guitar from Scratch: Two Months In",
    content="Two months of guitar practice notes and small wins.",
    category="Music",
    tags=["guitar", "practice"],
    image_urls=["/assets/004-guitar-learning-post.png"],
    min_image_count=1,
    created_at_ms=1790845200000,
)
EXPECTED_FOLLOW = XiaoShiLiuFollowAsset(
    follower_user_id=XIAOSHILIU_LOGIN_USER_ID,
    following_user_id=GUITAR_USER,
)

class XiaoShiLiuDeleteReplyFollowGuitarAuthorTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        XiaoShiLiuUserAsset(user_id=FOODIE_USER, nickname="Foodie Carter", email="foodie-carter@example.com"),
        XiaoShiLiuUserAsset(user_id=GUITAR_USER, nickname="Guitar Mentor", email="guitar-mentor@example.com"),
        TARGET_SECOND_POST,
        REMAINING_FIRST_POST,
        LATEST_POST,
        FOODIE_COMMENT,
        GUITAR_POST,
    )
    goal = (
        "Open XiaoShiLiu and delete my most recent post. After it is deleted, open my second "
        "post, find Foodie Carter's comment, and reply exactly \"hh\" to that comment. Then search "
        "the home page for \"Learning Guitar from Scratch: Two Months In\" and follow that post's author."
    )

    def criteria(self):
        return [
            AssetDeleted(LATEST_POST, task=self),
            AssetExists(EXPECTED_REPLY, task=self),
            AssetExists(EXPECTED_FOLLOW, task=self),
        ]
