from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import XiaoShiLiuPostAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


TARGET_POST = XiaoShiLiuPostAsset(author_user_id=XIAOSHILIU_LOGIN_USER_ID, title="Rainy Walk Snapshot", content="The path by the dorm looked calm after rain.", category="Campus Life", tags=["campus"], image_urls=["/assets/xiaoshiliu-delete-latest-post-latest-rain.png"], min_image_count=1, created_at_ms=1790845200000)
OLDER_PLANT_POST = XiaoShiLiuPostAsset(author_user_id=XIAOSHILIU_LOGIN_USER_ID, title="Window Plant Check", content="The dorm plant finally has new leaves.", category="Campus Life", tags=["dorm"], image_urls=["/assets/xiaoshiliu-delete-latest-post-older-plant.png"], min_image_count=1, created_at_ms=1790816400000)
OLDER_LIBRARY_POST = XiaoShiLiuPostAsset(author_user_id=XIAOSHILIU_LOGIN_USER_ID, title="Evening Library Seat", content="Found a quiet seat before dinner.", category="Study", tags=["Study"], image_urls=["/assets/xiaoshiliu-delete-latest-post-older-library.png"], min_image_count=1, created_at_ms=1790730000000)

class XiaoShiLiuDeleteLatestPostTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (OLDER_LIBRARY_POST, OLDER_PLANT_POST, TARGET_POST)
    goal = "Open XiaoShiLiu and delete my most recent post."

    def criteria(self):
        return [AssetDeleted(TARGET_POST, task=self)]
