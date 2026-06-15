from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpShopReviewAsset, HmdpUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SHOP_NAME = "Cafe Beignet on Royal Street"
REVIEW_TEXT = "Food is very delicious."


class HmdpReviewSecondFoodPriceCafeBeignetTask(BaseTask):
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
    expected_review = HmdpShopReviewAsset(
        user_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
        content=REVIEW_TEXT,
        score=4,
    )
    assets = (login_user,)

    goal = (
        'Open HMDP, go to Food, sort by Price from low to high, choose the second cheapest shop, '
        'and post a 4-star review saying exactly "Food is very delicious."'
    )

    def criteria(self):
        return [AssetExists(self.expected_review, task=self)]
