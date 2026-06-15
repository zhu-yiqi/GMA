from __future__ import annotations

from pathlib import Path
from gma.apps.hmdp import HMDP_LOGIN_PHONE
from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import DeviceFileAsset, HmdpShopFavoriteAsset, ImageContentExpectation, XiaoShiLiuPostAsset
from gma.evaluation import AnswerEquals, AssetExists, AssetMissing
from gma.tasks.base import BaseTask

POST_CONTENT = "Who lives near Maple Leaf Bar? Could you help me queue and get a number for me? I'll pay you."
IMAGE_FILENAME = 'restaurant-queue.jpeg'
EXPECTED_ANSWER = 'Meituan has the higher taste score: ZHANGLIANG SPICY HOTPOT.'

class HmdpXslMeituanRestaurantCompareTask(BaseTask):
    apps = {'HMDP', 'XiaoShiLiu', 'Meituan', 'Gallery'}
    difficulty = 'hard'
    category = ['Selection / Optimization Tasks', 'Conditional Tasks']
    snapshot = 'gma_ready_state'

    upload_image = DeviceFileAsset(app='Gallery', storage_dir='Pictures', filename=IMAGE_FILENAME, mime_type='image/jpeg', source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME))
    expected_post = XiaoShiLiuPostAsset(author_user_id=XIAOSHILIU_LOGIN_USER_ID, title='Restaurant Queue Help', content=POST_CONTENT, category='Food', min_image_count=1, expected_images=(ImageContentExpectation(source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME)),))
    assets = (upload_image,)
    user_interaction = 'If the agent asks which photo to upload, respond: Choose the latest image from Gallery. If it asks which score to compare, respond: Compare taste score.'

    goal = (
        "Open HMDP and compare Maple Leaf Bar's taste score with the nearest Meituan food store. If the HMDP score is higher, favorite Maple Leaf Bar. "
        'Open XiaoShiLiu and create a Food post titled "Restaurant Queue Help" with content "Who lives near Maple Leaf Bar? Could you help me queue and get a number for me? I\'ll pay you." and upload the latest image from Gallery. '
        'Then answer in exactly this format: "<app name> has the higher taste score: <restaurant name>.".'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_post, task=self),
            AssetMissing(HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name='Maple Leaf Bar'), task=self, weight=0.5),
            AnswerEquals(EXPECTED_ANSWER),
        ]
