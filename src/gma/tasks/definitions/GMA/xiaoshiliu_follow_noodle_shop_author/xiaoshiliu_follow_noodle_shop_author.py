from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import XiaoShiLiuFollowAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-campus-foodie"
AUTHOR = XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Campus Foodie", email="campus-foodie@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR, bio="Maps quick meals around campus.", location="Seed Campus")
OTHER_AUTHOR = XiaoShiLiuUserAsset(user_id="w4-snack-reviewer", nickname="Snack Reviewer", email="snack-reviewer@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR, bio="Reviews small snacks between classes.", location="Seed Campus")
TARGET_POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Hidden Gem Noodle Shop Behind Campus", content="A tiny noodle counter with quick service and rich broth.", category="Food", tags=["food", "noodles"], image_urls=["/assets/xiaoshiliu-follow-noodle-shop-author-noodle-shop.png"], min_image_count=1, created_at_ms=1790821800000)
DISTRACTOR_POST = XiaoShiLiuPostAsset(author_user_id="w4-snack-reviewer", title="Late-Night Rice Ball Stop", content="A reliable snack after group study.", category="Food", tags=["food", "snack"], image_urls=["/assets/xiaoshiliu-follow-noodle-shop-author-rice-ball.png"], min_image_count=1, created_at_ms=1790735400000)
EXPECTED_FOLLOW = XiaoShiLiuFollowAsset(follower_user_id=XIAOSHILIU_LOGIN_USER_ID, following_user_id=AUTHOR_ID)

class XiaoShiLiuFollowNoodleShopAuthorTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (AUTHOR, OTHER_AUTHOR, DISTRACTOR_POST, TARGET_POST)
    goal = 'Open XiaoShiLiu, find "Hidden Gem Noodle Shop Behind Campus" in Food, and follow the author of that post.'

    def criteria(self):
        return [AssetExists(EXPECTED_FOLLOW, task=self)]
