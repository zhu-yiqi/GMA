from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import DeviceFileAsset, HmdpBlogAsset, HmdpUserAsset, ImageContentExpectation
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SHOP_NAME = "Jim's South St"
POST_TITLE = "Jim's South St Visit"
POST_CONTENT = "Welcome everyone to come and taste! The ambiance and flavors are both excellent."


class HmdpCreateJimsSouthStFoodNoteTask(BaseTask):
    apps = {"HMDP", "Gallery"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = HmdpUserAsset(
        phone=HMDP_LOGIN_PHONE,
        password=HMDP_LOGIN_PASSWORD,
        nick_name=HMDP_LOGIN_NICKNAME,
        city="Austin",
        level=1,
    )
    food_photo = DeviceFileAsset(
        app="Gallery",
        storage_dir="Pictures",
        filename="hmdp-create-jims-south-st-food-note-hmdp-food.png",
        mime_type="image/png",
        source_path="assets/hmdp-create-jims-south-st-food-note-hmdp-food.png",
    )
    expected_blog = HmdpBlogAsset(
        author_phone=HMDP_LOGIN_PHONE,
        shop_name=SHOP_NAME,
        title=POST_TITLE,
        content=POST_CONTENT,
        expected_images=(ImageContentExpectation(source_path="assets/hmdp-create-jims-south-st-food-note-hmdp-food.png"),),
    )
    assets = (login_user, food_photo)

    goal = (
        "Open HMDP and create a food store-visit note linked to Jim's South St. "
        "Use the Gallery food photo, set the title exactly to \"Jim's South St Visit\", "
        "and set the note content exactly to \"Welcome everyone to come and taste! "
        "The ambiance and flavors are both excellent.\""
    )

    def criteria(self):
        return [AssetExists(self.expected_blog, task=self)]
