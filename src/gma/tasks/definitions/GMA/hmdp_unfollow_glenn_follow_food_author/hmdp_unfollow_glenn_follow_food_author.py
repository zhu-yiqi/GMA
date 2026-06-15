from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpFollowAsset, HmdpUserAsset
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


GLENN_PHONE = "5550101056"
GLENN_ID = 3900168
AUTHOR_PHONE = "5550101057"
AUTHOR_ID = 3910168
SHOP_NAME = "Jim's South St"
BLOG_TITLE = "Jim's South St Five-Star Note"
BLOG_TIME_MS = int(datetime(2026, 10, 1, 12, 18, tzinfo=UTC).timestamp() * 1000)


class HmdpUnfollowGlennFollowFoodAuthorTask(BaseTask):
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
    glenn = HmdpUserAsset(
        phone=GLENN_PHONE,
        password="123456",
        user_id=GLENN_ID,
        nick_name="Glenn Food",
        city="Philadelphia",
        level=2,
    )
    food_author = HmdpUserAsset(
        phone=AUTHOR_PHONE,
        password="123456",
        user_id=AUTHOR_ID,
        nick_name="Riley Food",
        city="Philadelphia",
        level=2,
    )
    initial_follow = HmdpFollowAsset(follower_phone=HMDP_LOGIN_PHONE, following_phone=GLENN_PHONE)
    seeded_blog = HmdpBlogAsset(
        author_phone=AUTHOR_PHONE,
        shop_name=SHOP_NAME,
        title=BLOG_TITLE,
        content="A five-star style note about Jim's South St.",
        created_at_ms=BLOG_TIME_MS,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    expected_follow = HmdpFollowAsset(follower_phone=HMDP_LOGIN_PHONE, following_phone=AUTHOR_PHONE)
    assets = (login_user, glenn, food_author, initial_follow, seeded_blog)

    goal = (
        'Open HMDP and go to your following list. Unfollow Glenn Food. '
        'Then search for Jim\'s South St, open the note titled "Jim\'s South St Five-Star Note", and follow its author.'
    )

    def criteria(self):
        return [
            AssetDeleted(self.initial_follow, task=self),
            AssetExists(self.expected_follow, task=self),
        ]
