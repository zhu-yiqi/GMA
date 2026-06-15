from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpShopFavoriteAsset, HmdpShopReviewAsset, HmdpUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


EXPENSIVE_FITNESS_SHOP = "Bill Jackson's Shop for Adventure"
REVIEW_SHOP = "24 Hour Fitness - Santa Barbara"
REVIEW_TEXT = "How does it taste?"
EXPECTED_ANSWER = "Bill Jackson's Shop for Adventure reviews: 5"


class HmdpFitnessExpensiveFavoriteReviewCountTask(BaseTask):
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
    expected_favorite = HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=EXPENSIVE_FITNESS_SHOP)
    expected_review = HmdpShopReviewAsset(
        user_phone=HMDP_LOGIN_PHONE,
        shop_name=REVIEW_SHOP,
        score=5,
        content=REVIEW_TEXT,
    )
    assets = (login_user,)

    goal = (
        "Open HMDP, go to Fitness, and favorite the most expensive Fitness shop, Bill Jackson's Shop for Adventure. "
        "Keep its review count for your final response. Then open 24 Hour Fitness - Santa Barbara and write a 5-star review saying exactly \"How does it taste?\". "
        "After finishing those actions, answer exactly \"Bill Jackson's Shop for Adventure reviews: 5\"."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_favorite, task=self),
            AnswerEquals(EXPECTED_ANSWER),
            AssetExists(self.expected_review, task=self),
        ]
