from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import HmdpBlogAsset, HmdpUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SHOP_NAME = "Heavenly Nails"
BLOG_TITLE = "Heavenly Nails recommendation"
BLOG_CONTENT = (
    "Heavenly Nails is a reliable local spot with a relaxed atmosphere and careful service. "
    "I recommend trying a classic manicure and asking about the latest seasonal colors."
)


class HmdpCreateHeavenlyNailsRecommendationTask(BaseTask):
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
    expected_blog = HmdpBlogAsset(
        author_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
        title=BLOG_TITLE,
        content=BLOG_CONTENT,
    )
    assets = (login_user,)

    goal = (
        "Open HMDP and create a note for Heavenly Nails. Set the title exactly to "
        "\"Heavenly Nails recommendation\" and set the content exactly to "
        "\"Heavenly Nails is a reliable local spot with a relaxed atmosphere and careful "
        "service. I recommend trying a classic manicure and asking about the latest seasonal "
        "colors.\""
    )

    def criteria(self):
        return [AssetExists(self.expected_blog, task=self)]
