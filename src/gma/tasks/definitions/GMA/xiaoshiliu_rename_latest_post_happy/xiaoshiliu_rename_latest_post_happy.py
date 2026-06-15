from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import XiaoShiLiuPostAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


OLD_POST = XiaoShiLiuPostAsset(
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    title="Weekend Desk Reset",
    content="Rearranged my study corner before the new week.",
    category="Study",
    tags=["study", "desk"],
    image_urls=["/assets/xiaoshiliu-rename-latest-post-happy-latest-library-desk.png"],
    min_image_count=1,
    created_at_ms=1790845200000,
)
EXPECTED_POST = XiaoShiLiuPostAsset(
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    title="Happy",
    content=OLD_POST.content,
    category="Study",
    tags=OLD_POST.tags,
    image_urls=OLD_POST.image_urls,
    min_image_count=1,
)
OLDER_CAFE_POST = XiaoShiLiuPostAsset(
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    title="Courtyard Coffee Break",
    content="Short pause after finishing a chapter summary.",
    category="Campus Life",
    tags=["campus"],
    image_urls=["/assets/xiaoshiliu-rename-latest-post-happy-older-cafe.png"],
    min_image_count=1,
    created_at_ms=1790814600000,
)
OLDER_BIKE_POST = XiaoShiLiuPostAsset(
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    title="Sunset Bike Rack",
    content="Quiet evening outside the library.",
    category="Campus Life",
    tags=["campus"],
    image_urls=["/assets/xiaoshiliu-rename-latest-post-happy-older-bike.png"],
    min_image_count=1,
    created_at_ms=1790728200000,
)

class XiaoShiLiuRenameLatestPostHappyTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (OLDER_BIKE_POST, OLDER_CAFE_POST, OLD_POST)
    goal = 'Open XiaoShiLiu and rename the title of my most recent post to "Happy".'

    def criteria(self):
        return [AssetModified(OLD_POST, EXPECTED_POST, task=self)]
