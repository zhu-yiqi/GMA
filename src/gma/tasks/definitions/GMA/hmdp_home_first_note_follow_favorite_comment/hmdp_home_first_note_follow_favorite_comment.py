from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpBlogCommentAsset, HmdpFollowAsset, HmdpShopFavoriteAsset, HmdpUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


TARGET_PHONE = "5550101045"
TARGET_USER_ID = 8068
SHOP_NAME = "Jim's South St"
BLOG_TITLE = "Restaurant Ambiance Note"
BLOG_CONTENT = "A home-page note about the restaurant ambiance."
COMMENT_TEXT = "How is the ambiance of this restaurant?"
BLOG_TIME_MS = int(datetime(2026, 10, 1, 12, 20, tzinfo=UTC).timestamp() * 1000)


class HmdpHomeFirstNoteFollowFavoriteCommentTask(BaseTask):
    apps = {"HMDP"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = HmdpUserAsset(
        phone=HMDP_LOGIN_PHONE,
        password=HMDP_LOGIN_PASSWORD,
        nick_name=HMDP_LOGIN_NICKNAME,
        city="Austin",
        level=1,
    )
    target_user = HmdpUserAsset(
        phone=TARGET_PHONE,
        password="123456",
        user_id=TARGET_USER_ID,
        nick_name="Maya Home",
        city="Philadelphia",
        level=1,
    )
    seeded_home_blog = HmdpBlogAsset(
        author_phone=TARGET_PHONE,
        shop_name=SHOP_NAME,
        title=BLOG_TITLE,
        content=BLOG_CONTENT,
        liked=999,
        created_at_ms=BLOG_TIME_MS,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    expected_follow = HmdpFollowAsset(
        follower_phone=HMDP_LOGIN_PHONE,
        following_phone=TARGET_PHONE,
    )
    expected_favorite = HmdpShopFavoriteAsset(
        user_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
    )
    expected_comment = HmdpBlogCommentAsset(
        blog_title=BLOG_TITLE,
        blog_author_phone=TARGET_PHONE,
        author_phone=HMDP_LOGIN_PHONE,
        content=COMMENT_TEXT,
    )
    assets = (login_user, target_user, seeded_home_blog)

    goal = (
        "Open HMDP's Home page, open the first note, follow the note author, "
        "favorite the linked store, and comment exactly \"How is the ambiance of this restaurant?\""
    )

    def criteria(self):
        return [
            AssetExists(self.expected_follow, task=self),
            AssetExists(self.expected_favorite, task=self),
            AssetExists(self.expected_comment, task=self),
        ]
