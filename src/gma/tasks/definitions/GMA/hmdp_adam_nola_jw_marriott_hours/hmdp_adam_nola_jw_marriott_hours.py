from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpBlogLikeAsset, HmdpFollowAsset, HmdpShopFavoriteAsset, HmdpShopReviewAsset, HmdpUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


ADAM_PHONE = "5550101040"
ADAM_ID = 3900170
SHOP_NAME = "NOLA Restaurant"
BLOG_TITLE = "Quiet Music at NOLA Restaurant"
COMMENT_TEXT = "Is the music quiet?"
EXPECTED_ANSWER = "JW MarriottTucson Starr Pass Resort & Spa business hours: 00:00-00:00"
BLOG_TIME_MS = int(datetime(2026, 10, 1, 12, 20, tzinfo=UTC).timestamp() * 1000)


class HmdpAdamNolaJwMarriottHoursTask(BaseTask):
    apps = {"HMDP"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    login_user = HmdpUserAsset(
        phone=HMDP_LOGIN_PHONE,
        password=HMDP_LOGIN_PASSWORD,
        nick_name=HMDP_LOGIN_NICKNAME,
        city="Austin",
        level=1,
    )
    adam = HmdpUserAsset(
        phone=ADAM_PHONE,
        password="123456",
        user_id=ADAM_ID,
        nick_name="Adam Music",
        city="New Orleans",
        level=2,
    )
    seeded_blog = HmdpBlogAsset(
        author_phone=ADAM_PHONE,
        shop_name=SHOP_NAME,
        title=BLOG_TITLE,
        content="A quiet-music note about dinner at NOLA Restaurant.",
        created_at_ms=BLOG_TIME_MS,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    expected_like = HmdpBlogLikeAsset(
        user_phone=HMDP_LOGIN_PHONE,
        blog_title=BLOG_TITLE,
        blog_author_phone=ADAM_PHONE,
    )
    expected_follow = HmdpFollowAsset(follower_phone=HMDP_LOGIN_PHONE, following_phone=ADAM_PHONE)
    expected_review = HmdpShopReviewAsset(
        user_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
        score=5,
        content=COMMENT_TEXT,
    )
    expected_favorite = HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=SHOP_NAME)
    assets = (login_user, adam, seeded_blog)

    goal = (
        'Open HMDP, search for Adam Music, and open the note titled "Quiet Music at NOLA Restaurant". '
        'Like the note, follow Adam Music, open NOLA Restaurant from the note, write a 5-star review saying exactly "Is the music quiet?", and favorite NOLA Restaurant. '
        'Then check JW MarriottTucson Starr Pass Resort & Spa and answer in exactly this format: "JW MarriottTucson Starr Pass Resort & Spa business hours: <business hours>".'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_like, task=self),
            AssetExists(self.expected_follow, task=self),
            AssetExists(self.expected_review, task=self),
            AssetExists(self.expected_favorite, task=self),
            AnswerEquals(EXPECTED_ANSWER),
        ]
