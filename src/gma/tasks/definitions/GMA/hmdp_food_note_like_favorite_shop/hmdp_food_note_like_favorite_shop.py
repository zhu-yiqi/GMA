from __future__ import annotations

from pathlib import Path
from gma.apps.hmdp import HMDP_LOGIN_PHONE
from gma.assets import DeviceFileAsset, HmdpBlogAsset, HmdpBlogLikeAsset, HmdpShopFavoriteAsset, HmdpUserAsset, ImageContentExpectation
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask

BLOG_TEXT = 'I ordered the grilled salmon, and it was exquisite. The fish was perfectly seared with a crispy skin, yet the inside remained moist and flaky. Paired with a zesty lemon dill sauce, every bite was a burst of fresh flavors. Highly recommended!'
EXPECTED_ANSWER = 'Acme Oyster House average price: 70.'

class HmdpFoodNoteLikeFavoriteShopTask(BaseTask):
    apps = {'HMDP', 'Files'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    food_file = DeviceFileAsset(app='Files', storage_dir='Pictures', filename='salmon-dinner.jpeg', mime_type='image/jpeg', source_path=str(Path(__file__).with_name('assets') / 'salmon-dinner.jpeg'))
    review_author = HmdpUserAsset(phone='5550101043', nick_name='Avery Reed', city='Austin')
    author_blog = HmdpBlogAsset(author_phone='5550101043', shop_name='Acme Oyster House', title="Avery\'s Seafood Note", content='A short note about Acme Oyster House.', images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'])
    expected_blog = HmdpBlogAsset(author_phone=HMDP_LOGIN_PHONE, shop_name='Acme Oyster House', title='Food', content=BLOG_TEXT, images=[], expected_images=(ImageContentExpectation(source_path=str(Path(__file__).with_name('assets') / 'salmon-dinner.jpeg')),))
    assets = (food_file, review_author, author_blog)
    user_interaction = 'If the agent asks which photo to choose, respond: Choose the latest image from the device.'

    goal = f'Open HMDP and post a note titled "Food" linked to Acme Oyster House with content "{BLOG_TEXT}" and upload the latest image from the device. Then find Avery Reed, like the note titled "Avery\'s Seafood Note", favorite Acme Oyster House, and answer exactly "{EXPECTED_ANSWER}".'

    def criteria(self):
        return [
            AssetExists(self.expected_blog, task=self),
            AssetExists(HmdpBlogLikeAsset(user_phone=HMDP_LOGIN_PHONE, blog_title="Avery\'s Seafood Note", blog_author_phone='5550101043'), task=self),
            AssetExists(HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name='Acme Oyster House'), task=self),
            AnswerEquals(EXPECTED_ANSWER),
        ]
