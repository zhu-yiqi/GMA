from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, HmdpShopFavoriteAsset, HmdpShopReviewAsset, HmdpUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask

EXPECTED_ANSWER = 'Bars checked: Rum Sugar Lime avg price 70 rating 4.5; Narwhal\'s Crafted avg price 70 rating 4.5; The Good Lion avg price 70 rating 4.5.'
BEAUTY_SHOP = 'Volume Hair Studio'
BAR_MESSAGE = 'I just discovered a great bar-we should go sometime, and get haircuts too. Rum Sugar Lime, hours 00:00-00:00.'
HANNAH_REED = 'hannah-reed-row257'
DM_ROOM = elementx_user_id(HANNAH_REED)

class HmdpElementXBarBeautySummaryTask(BaseTask):
    apps = {'HMDP', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    hmdp_user = HmdpUserAsset(phone=HMDP_LOGIN_PHONE, password=HMDP_LOGIN_PASSWORD, nick_name=HMDP_LOGIN_NICKNAME, city='Austin', level=1)
    dm_user = ElementXUserAsset(username=HANNAH_REED, password='password', display_name='Hannah Reed')
    assets = (hmdp_user, dm_user)

    goal = (
        'Open HMDP, check these three Bar shops: Rum Sugar Lime, Narwhal\'s Crafted, and The Good Lion, and keep their names, average prices, and ratings for your final response. '
        'Favorite Rum Sugar Lime, then in Beauty & Hair favorite Volume Hair Studio and post a 4-star review saying "How is the haircut quality at this shop?". '
        'Open ElementX and send Hannah Reed a message about that favorited bar in exactly this format: "I just discovered a great bar-we should go sometime, and get haircuts too. <bar name>, hours <hours>." '
        'After finishing those actions, answer in exactly this format: "Bars checked: <bar 1> avg price <price 1> rating <rating 1>; <bar 2> avg price <price 2> rating <rating 2>; <bar 3> avg price <price 3> rating <rating 3>.".'
    )

    def criteria(self):
        return [
            AnswerEquals(EXPECTED_ANSWER),
            AssetExists(HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name="Rum Sugar Lime"), task=self),
            AssetExists(HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=BEAUTY_SHOP), task=self),
            AssetExists(HmdpShopReviewAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=BEAUTY_SHOP, content='How is the haircut quality at this shop?', score=4), task=self),
            AssetExists(ElementXRoomAsset(name='Hannah Reed', room_type='dm', creator_username='testuser', creator_password='testpass123', members=[HANNAH_REED]), task=self),
            AssetExists(ElementXMessageAsset(room=DM_ROOM, sender_username='testuser', sender_password='testpass123', text=BAR_MESSAGE), task=self),
        ]
