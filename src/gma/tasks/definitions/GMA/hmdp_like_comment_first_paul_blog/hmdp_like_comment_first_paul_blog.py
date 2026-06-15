from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpBlogCommentAsset, HmdpBlogLikeAsset, HmdpUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


PAUL_PHONE = "5550101049"
PAUL_USER_ID = 1020
SHOP_NAME = "Jim's South St"
BLOG_TITLE = "Paul's HMDP Food Note"
BLOG_CONTENT = "A short seeded restaurant note for Paul search tasks."
COMMENT_TEXT = "Well written."
BLOG_TIME_MS = int(datetime(2026, 10, 1, 12, 10, tzinfo=UTC).timestamp() * 1000)


class HmdpLikeCommentFirstPaulBlogTask(BaseTask):
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
    paul_user = HmdpUserAsset(
        phone=PAUL_PHONE,
        password="123456",
        user_id=PAUL_USER_ID,
        nick_name="Paul",
        city="Philadelphia",
        level=1,
    )
    seeded_blog = HmdpBlogAsset(
        author_phone=PAUL_PHONE,
        shop_name=SHOP_NAME,
        title=BLOG_TITLE,
        content=BLOG_CONTENT,
        created_at_ms=BLOG_TIME_MS,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    expected_like = HmdpBlogLikeAsset(
        user_phone=HMDP_LOGIN_PHONE,
        blog_title=BLOG_TITLE,
        blog_author_phone=PAUL_PHONE,
    )
    expected_comment = HmdpBlogCommentAsset(
        blog_title=BLOG_TITLE,
        blog_author_phone=PAUL_PHONE,
        author_phone=HMDP_LOGIN_PHONE,
        content=COMMENT_TEXT,
    )
    assets = (login_user, paul_user, seeded_blog)

    goal = (
        "Open HMDP and search for \"Paul\". Select the first post from the first blogger found, "
        "like it, and comment exactly \"Well written.\""
    )

    def criteria(self):
        return [
            AssetExists(self.expected_like, task=self),
            AssetExists(self.expected_comment, task=self),
        ]
