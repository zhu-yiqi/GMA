from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-wellness-author"
AUTHOR = XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Campus Wellness", email="campus-wellness@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR, bio="Simple routines for busy students.", location="Seed Campus")
TARGET_POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="10-Minute Dorm Room Stretching Routine", content="A short no-equipment stretch sequence for a quiet dorm room.", category="Fitness", tags=["recommended", "wellness"], image_urls=["/assets/xiaoshiliu-like-dorm-stretching-routine-stretch-routine.png"], min_image_count=1, created_at_ms=1790820000000)
DISTRACTOR_POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Hydration Reminder Before Class", content="Pack a bottle before leaving for morning lectures.", category="Fitness", tags=["recommended", "wellness"], image_urls=["/assets/xiaoshiliu-like-dorm-stretching-routine-hydration.png"], min_image_count=1, created_at_ms=1790733600000)
EXPECTED_LIKE = XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=TARGET_POST.title, post_author_user_id=AUTHOR_ID)

class XiaoShiLiuLikeDormStretchingRoutineTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (AUTHOR, DISTRACTOR_POST, TARGET_POST)
    goal = 'Open XiaoShiLiu, find "10-Minute Dorm Room Stretching Routine" in Fitness, and like it.'

    def criteria(self):
        return [AssetExists(EXPECTED_LIKE, task=self)]
