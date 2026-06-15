from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpBlogLikeAsset, HmdpShopFavoriteAsset, HmdpShopReviewAsset, HmdpUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


SHOP_NAME = "Royal Thai Massage"
AUTHOR_PHONE = "5550101055"
AUTHOR_ID = 3900166
BLOG_TITLE = "Royal Thai Calm Room Note"
REVIEW_TEXT = "It is not true that water is ice; they are different states of matter."
EXPECTED_ANSWER = "Royal Thai Massage address: 3204 State St, Ste A"
BLOG_TIME_MS = int(datetime(2026, 10, 1, 12, 16, tzinfo=UTC).timestamp() * 1000)


class HmdpRoyalThaiReviewLikeFavoriteTask(BaseTask):
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
    note_author = HmdpUserAsset(
        phone=AUTHOR_PHONE,
        password="123456",
        user_id=AUTHOR_ID,
        nick_name="Riley Royal",
        city="Santa Barbara",
        level=2,
    )
    seeded_blog = HmdpBlogAsset(
        author_phone=AUTHOR_PHONE,
        shop_name=SHOP_NAME,
        title=BLOG_TITLE,
        content="A note about a quiet massage room.",
        created_at_ms=BLOG_TIME_MS,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    expected_review = HmdpShopReviewAsset(
        user_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
        score=5,
        content=REVIEW_TEXT,
    )
    expected_like = HmdpBlogLikeAsset(
        user_phone=HMDP_LOGIN_PHONE,
        blog_title=BLOG_TITLE,
        blog_author_phone=AUTHOR_PHONE,
    )
    expected_favorite = HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=SHOP_NAME)
    assets = (login_user, note_author, seeded_blog)

    goal = (
        'Open HMDP and search for Royal Thai Massage. Write a 5-star review saying exactly "It is not true that water is ice; they are different states of matter.". '
        'Then find and like the note titled "Royal Thai Calm Room Note", favorite Royal Thai Massage, and answer in exactly this format: "Royal Thai Massage address: <address>".'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_review, task=self),
            AssetExists(self.expected_like, task=self),
            AssetExists(self.expected_favorite, task=self),
            AnswerEquals(EXPECTED_ANSWER),
        ]
