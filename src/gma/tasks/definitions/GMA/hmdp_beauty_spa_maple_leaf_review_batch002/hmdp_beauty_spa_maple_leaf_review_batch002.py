from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpShopFavoriteAsset, HmdpShopReviewAsset, HmdpUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


MAPLE_LEAF_BAR = "Maple Leaf Bar"
REVIEW_TEXT = "This place has a lovely setting."
EXPECTED_ANSWER = "Highest-rated Beauty SPA: Laser Remedy MedSpa, Spa Toscana, Volume Hair Studio"


class HmdpBeautySpaMapleLeafReviewBatch002Task(BaseTask):
    apps = {"HMDP"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        HmdpUserAsset(
            phone=HMDP_LOGIN_PHONE,
            password=HMDP_LOGIN_PASSWORD,
            nick_name=HMDP_LOGIN_NICKNAME,
            city="Austin",
            level=1,
        ),
    )
    goal = (
        "Open HMDP and compare the top three Beauty SPA shops when sorted by Popular; keep the highest-rating result for your final response. "
        "If more than one shop ties, list all tied names in the order shown. "
        "Then search for Maple Leaf Bar, write a 4-star review saying \"This place has a lovely setting.\", and favorite the shop. "
        "After finishing those actions, answer exactly using this format: \"Highest-rated Beauty SPA: <shop name or names separated by comma and space>\"."
    )

    def criteria(self):
        return [
            AnswerEquals(EXPECTED_ANSWER),
            AssetExists(
                HmdpShopReviewAsset(
                    user_phone=HMDP_LOGIN_PHONE,
                    shop_name=MAPLE_LEAF_BAR,
                    score=4,
                    content=REVIEW_TEXT,
                ),
                task=self,
            ),
            AssetExists(
                HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=MAPLE_LEAF_BAR),
                task=self,
            ),
        ]
