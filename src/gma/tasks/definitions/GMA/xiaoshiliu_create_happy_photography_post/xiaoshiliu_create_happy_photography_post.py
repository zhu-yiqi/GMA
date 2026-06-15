from __future__ import annotations

import base64
import shlex
from pathlib import Path

from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import DeviceFileAsset, ImageContentExpectation, XiaoShiLiuCollectionAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


IMAGE_FILE = "001-happy-photography-upload.png"
UPLOAD_IMAGE = DeviceFileAsset(
    app="Gallery",
    storage_dir="Pictures",
    filename=IMAGE_FILE,
    mime_type="image/png",
    source_path=f"assets/{IMAGE_FILE}",
)
EXPECTED_POST = XiaoShiLiuPostAsset(
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    title="Happy",
    content="beautiful",
    category="Photography",
    min_image_count=1,
    expected_images=(ImageContentExpectation(source_path=f"assets/{IMAGE_FILE}"),),
)
EXPECTED_LIKE = XiaoShiLiuLikeAsset(
    user_id=XIAOSHILIU_LOGIN_USER_ID,
    post_title="Happy",
    post_author_user_id=XIAOSHILIU_LOGIN_USER_ID,
)
EXPECTED_COLLECTION = XiaoShiLiuCollectionAsset(
    user_id=XIAOSHILIU_LOGIN_USER_ID,
    post_title="Happy",
    post_author_user_id=XIAOSHILIU_LOGIN_USER_ID,
)


class XiaoShiLiuCreateHappyPhotographyPostTask(BaseTask):
    apps = {"XiaoShiLiu", "Gallery"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (UPLOAD_IMAGE,)
    user_interaction = (
        "If the agent asks which image to use for the XiaoShiLiu post, answer exactly: "
        "Use the happy photography image. Do not provide unrelated information."
    )
    goal = (
        "Open XiaoShiLiu and create a published image post titled \"Happy\" with content "
        "\"beautiful\" in the Photography category. Upload the happy photography "
        "image, then like and bookmark the post you just published."
    )

    def criteria(self):
        return [
            AssetExists(EXPECTED_POST, task=self),
            AssetExists(EXPECTED_LIKE, task=self),
            AssetExists(EXPECTED_COLLECTION, task=self),
        ]
