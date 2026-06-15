from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpBlogLikeAsset, HmdpFollowAsset, HmdpUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SHOP_NAME = "Heavenly Nails"
AUTHOR_PHONE = "5550101044"
AUTHOR_ID = 3900169
SHOP_BLOG_TITLE = "Nora's Heavenly Nails Review"
PROFILE_SECOND_TITLE = "My Nail Care Note Two"
BASE_TIME_MS = int(datetime(2026, 10, 1, 12, 19, tzinfo=UTC).timestamp() * 1000)


class HmdpHeavenlyNailsFollowLikeProfileNoteTask(BaseTask):
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
    nails_author = HmdpUserAsset(
        phone=AUTHOR_PHONE,
        password="123456",
        user_id=AUTHOR_ID,
        nick_name="Nora Nails",
        city="Tampa",
        level=2,
    )
    shop_blog = HmdpBlogAsset(
        author_phone=AUTHOR_PHONE,
        shop_name=SHOP_NAME,
        title=SHOP_BLOG_TITLE,
        content="A seeded Heavenly Nails note for follow tasks.",
        created_at_ms=BASE_TIME_MS,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    own_blog_one = HmdpBlogAsset(
        author_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
        title="My Nail Care Note One",
        content="First seeded profile note.",
        created_at_ms=BASE_TIME_MS + 1000,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    own_blog_two = HmdpBlogAsset(
        author_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
        title=PROFILE_SECOND_TITLE,
        content="Second seeded profile note.",
        created_at_ms=BASE_TIME_MS + 2000,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    own_blog_three = HmdpBlogAsset(
        author_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
        title="My Nail Care Note Three",
        content="Third seeded profile note.",
        created_at_ms=BASE_TIME_MS + 3000,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    expected_follow = HmdpFollowAsset(follower_phone=HMDP_LOGIN_PHONE, following_phone=AUTHOR_PHONE)
    expected_like = HmdpBlogLikeAsset(
        user_phone=HMDP_LOGIN_PHONE,
        blog_title=PROFILE_SECOND_TITLE,
        blog_author_phone=HMDP_LOGIN_PHONE,
    )
    assets = (login_user, nails_author, shop_blog, own_blog_one, own_blog_two, own_blog_three)

    goal = (
        "Open HMDP, search for Heavenly Nails, and open the note titled "
        "\"Nora's Heavenly Nails Review\". Follow the note author Nora Nails. Then go "
        "to my personal profile and like my note titled \"My Nail Care Note Two\"."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_follow, task=self),
            AssetExists(self.expected_like, task=self),
        ]
