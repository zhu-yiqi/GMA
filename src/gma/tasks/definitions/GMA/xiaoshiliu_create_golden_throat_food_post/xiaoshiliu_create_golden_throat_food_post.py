from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import DeviceFileAsset, ImageContentExpectation, XiaoShiLiuPostAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class XiaoShiLiuCreateGoldenThroatFoodPostTask(BaseTask):
    apps = {"XiaoShiLiu", "Gallery"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    upload_image = DeviceFileAsset(
        app="Gallery",
        storage_dir="Pictures",
        filename="xiaoshiliu-create-golden-throat-food-post-golden-throat.png",
        mime_type="image/png",
        source_path="assets/xiaoshiliu-create-golden-throat-food-post-golden-throat.png",
    )
    expected_post = XiaoShiLiuPostAsset(
        author_user_id=XIAOSHILIU_LOGIN_USER_ID,
        title="golden throat",
        content="very good",
        category="Food",
        min_image_count=1,
        expected_images=(ImageContentExpectation(source_path="assets/xiaoshiliu-create-golden-throat-food-post-golden-throat.png"),),
    )
    assets = (upload_image,)

    goal = (
        "Open XiaoShiLiu and create a new image post using the first Gallery photo. "
        "Set the title exactly to \"golden throat\", the content exactly to \"very good\", "
        "and the category to Food."
    )

    def criteria(self):
        return [AssetExists(self.expected_post, task=self)]
