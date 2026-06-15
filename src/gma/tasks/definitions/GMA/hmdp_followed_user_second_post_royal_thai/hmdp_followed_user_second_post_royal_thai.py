from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpBlogLikeAsset, HmdpFollowAsset, HmdpShopReviewAsset, HmdpUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


AUTHOR_PHONE = "5550101042"
AUTHOR_ID = 3900173
SHOP_NAME = "Royal Thai Massage"
SECOND_TITLE = "Royal Thai Massage Follow-Up Note"
REVIEW_TEXT = "Well said!"
EXPECTED_ANSWER = "Royal Thai Massage business hours: 00:00-00:00"
BASE_TIME_MS = int(datetime(2026, 10, 1, 12, 23, tzinfo=UTC).timestamp() * 1000)


class HmdpFollowedUserSecondPostRoyalThaiTask(BaseTask):
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
    followed_user = HmdpUserAsset(
        phone=AUTHOR_PHONE,
        password="123456",
        user_id=AUTHOR_ID,
        nick_name="Morgan Royal",
        city="Santa Barbara",
        level=2,
    )
    initial_follow = HmdpFollowAsset(follower_phone=HMDP_LOGIN_PHONE, following_phone=AUTHOR_PHONE)
    first_blog = HmdpBlogAsset(
        author_phone=AUTHOR_PHONE,
        shop_name=SHOP_NAME,
        title="Royal Thai Massage First Visit Note",
        content="First visit note about Royal Thai Massage.",
        created_at_ms=BASE_TIME_MS,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    second_blog = HmdpBlogAsset(
        author_phone=AUTHOR_PHONE,
        shop_name=SHOP_NAME,
        title=SECOND_TITLE,
        content="Follow-up note about Royal Thai Massage.",
        created_at_ms=BASE_TIME_MS + 1000,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    expected_like = HmdpBlogLikeAsset(
        user_phone=HMDP_LOGIN_PHONE,
        blog_title=SECOND_TITLE,
        blog_author_phone=AUTHOR_PHONE,
    )
    expected_review = HmdpShopReviewAsset(
        user_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
        score=5,
        content=REVIEW_TEXT,
    )
    assets = (login_user, followed_user, initial_follow, first_blog, second_blog)

    goal = (
        'Open HMDP, go to the profile for the user I follow named Morgan Royal, and open the post titled "Royal Thai Massage Follow-Up Note". '
        'Like that post, check Royal Thai Massage, and write a 5-star shop review saying exactly "Well said!". '
        'After finishing those actions, answer in exactly this format: "Royal Thai Massage business hours: <business hours>".'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_like, task=self),
            AnswerEquals(EXPECTED_ANSWER),
            AssetExists(self.expected_review, task=self),
        ]
