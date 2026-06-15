from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_PHONE
from gma.assets import ElementXMessageAsset, ElementXPollAsset, ElementXRoomAsset, ElementXUserAsset, HmdpBlogAsset, HmdpShopFavoriteAsset, HmdpUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

ROOM_ALIAS = 'shop'
STORE = 'Maple Leaf Bar'
MESSAGE = f'{STORE}: What do you think of this store? @room'

class HmdpElementXDeleteNoteShopPollTask(BaseTask):
    apps = {'HMDP', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    blog = HmdpBlogAsset(author_phone=HMDP_LOGIN_PHONE, shop_name=STORE, title='Recent Note To Delete', content='This is the recent note that should be deleted.', images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'])
    friend = ElementXUserAsset(username='riley-park-shop', password='password', display_name='Riley Park')
    assets = (HmdpUserAsset(phone=HMDP_LOGIN_PHONE, nick_name='Owner'), blog, friend)

    goal = f'Open HMDP and favorite Maple Leaf Bar. Then open ElementX, create a group chat named "shop" with Riley Park, send exactly "{MESSAGE}" with a room mention, and create a poll titled "Store opinion" with options good and bad.'

    def criteria(self):
        return [
            AssetExists(HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=STORE), task=self),
            AssetExists(ElementXRoomAsset(name='shop', room_type='group', creator_username='testuser', creator_password='testpass123', members=['riley-park-shop'], alias_localpart=ROOM_ALIAS), task=self),
            AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=MESSAGE, mentions_room=True), task=self),
            AssetExists(ElementXPollAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', question='Store opinion', options=['good', 'bad']), task=self),
        ]
