from __future__ import annotations

from pathlib import Path
from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import DeviceFileAsset, ImageContentExpectation, XiaoShiLiuCommentAsset, XiaoShiLiuPostAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

IMAGE_FILENAME = 'fitness-gym.jpeg'
SHOP_NAME = '24 Hour Fitness - Santa Barbara'
REVIEW_SENTENCE = 'g'
POST_CONTENT = REVIEW_SENTENCE + ' How are the facilities at this gym?'

class HmdpXslFitnessReviewRepostTask(BaseTask):
    apps = {'HMDP', 'XiaoShiLiu', 'Gallery'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    image = DeviceFileAsset(app='Gallery', storage_dir='Pictures', filename=IMAGE_FILENAME, mime_type='image/jpeg', source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME))
    expected_post = XiaoShiLiuPostAsset(author_user_id=XIAOSHILIU_LOGIN_USER_ID, title='Work out / Fitness', content=POST_CONTENT, category='Fitness', min_image_count=1, expected_images=(ImageContentExpectation(source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME)),))
    assets = (image,)

    goal = f'Open HMDP and read the first review for {SHOP_NAME}. Then open XiaoShiLiu and create a Fitness post titled "Work out / Fitness" whose content is the first sentence of that review followed by one space and "How are the facilities at this gym?". Upload the latest image from Gallery. Comment on your new post exactly "The content comes from reviews of this shop."'

    def criteria(self):
        return [
            AssetExists(self.expected_post, task=self),
            AssetExists(XiaoShiLiuCommentAsset(post_title='Work out / Fitness', post_author_user_id=XIAOSHILIU_LOGIN_USER_ID, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content='The content comes from reviews of this shop.'), task=self),
        ]
