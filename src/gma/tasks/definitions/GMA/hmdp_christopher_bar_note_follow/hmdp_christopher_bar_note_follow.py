from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpBlogLikeAsset, HmdpFollowAsset, HmdpUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


SHOP_NAME = "Rum Sugar Lime"
CHRISTOPHER_PHONE = "5550101041"
CHRISTOPHER_ID = 3900167
BLOG_TITLE = "Rum Sugar Lime Visit Note"
EXPECTED_ANSWER = "Rum Sugar Lime taste rating: 4.9"
BLOG_TIME_MS = int(datetime(2026, 10, 1, 12, 17, tzinfo=UTC).timestamp() * 1000)


class HmdpChristopherBarNoteFollowTask(BaseTask):
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
    christopher = HmdpUserAsset(
        phone=CHRISTOPHER_PHONE,
        password="123456",
        user_id=CHRISTOPHER_ID,
        nick_name="Christopher Bar",
        city="Reno",
        level=2,
    )
    seeded_blog = HmdpBlogAsset(
        author_phone=CHRISTOPHER_PHONE,
        shop_name=SHOP_NAME,
        title=BLOG_TITLE,
        content="Christopher's visit note about Rum Sugar Lime.",
        created_at_ms=BLOG_TIME_MS,
    images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
    )
    expected_like = HmdpBlogLikeAsset(
        user_phone=HMDP_LOGIN_PHONE,
        blog_title=BLOG_TITLE,
        blog_author_phone=CHRISTOPHER_PHONE,
    )
    expected_follow = HmdpFollowAsset(follower_phone=HMDP_LOGIN_PHONE, following_phone=CHRISTOPHER_PHONE)
    assets = (login_user, christopher, seeded_blog)

    goal = (
        'Open HMDP and search for Rum Sugar Lime in Bar; keep its taste rating for your final response. '
        'Then search for Christopher Bar, open the note titled "Rum Sugar Lime Visit Note", like that note, and follow Christopher Bar if you are not already following this profile. '
        'After finishing those actions, answer in exactly this format: "Rum Sugar Lime taste rating: <taste rating>".'
    )

    def criteria(self):
        return [
            AnswerEquals(EXPECTED_ANSWER),
            AssetExists(self.expected_like, task=self),
            AssetExists(self.expected_follow, task=self),
        ]
