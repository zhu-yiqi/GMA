from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpFollowAsset, HmdpUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


EXPECTED_ANSWER = "Royal Thai Massage average price: 70"
BASE_TIME_MS = int(datetime(2026, 10, 1, 12, 25, tzinfo=UTC).timestamp() * 1000)
JASONS = (
    ("5550101046", 3901751, "Jason North", True),
    ("5550101047", 3901752, "Jason South", True),
    ("5550101048", 3901753, "Jason East", True),
    ("5550101049", 3901754, "Jason West", False),
    ("5550101050", 3901755, "Jason Central", False),
)


class HmdpJasonProfilesRoyalThaiPriceTask(BaseTask):
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
    jason_users = tuple(
        HmdpUserAsset(
            phone=phone,
            password="123456",
            user_id=user_id,
            nick_name=name,
            city="Santa Barbara",
            level=2,
        )
        for phone, user_id, name, _has_note in JASONS
    )
    jason_blogs = tuple(
        HmdpBlogAsset(
            author_phone=phone,
            shop_name="Royal Thai Massage",
            title=f"{name} Royal Thai Visit Note",
            content=f"A Royal Thai Massage note by {name}.",
            created_at_ms=BASE_TIME_MS + index * 1000,
        images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'],
        )
        for index, (phone, _user_id, name, has_note) in enumerate(JASONS)
        if has_note
    )
    expected_follows = tuple(
        HmdpFollowAsset(follower_phone=HMDP_LOGIN_PHONE, following_phone=phone)
        for phone, _user_id, _name, has_note in JASONS
        if has_note
    )
    assets = (login_user, *jason_users, *jason_blogs)

    goal = (
        'Open HMDP and search for Jason profiles. Visit Jason North, Jason South, Jason East, Jason West, and Jason Central. '
        'Follow only the Jason profiles that have Royal Thai Massage notes. '
        'Then find Royal Thai Massage and answer in exactly this format: "Royal Thai Massage average price: <average price>".'
    )

    def criteria(self):
        return [
            *(AssetExists(follow, task=self) for follow in self.expected_follows),
            AnswerEquals(EXPECTED_ANSWER),
        ]
