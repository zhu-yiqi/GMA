from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import ElementXMessageAsset, ElementXPollAsset, ElementXRoomAsset, ElementXUserAsset, HmdpShopFavoriteAsset, HmdpUserAsset, MeituanAddressAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask

ANSWER = 'First bookmarked HMDP store: Maple Leaf Bar.'
COMMENT = 'Maple Leaf Bar is the first bookmarked store. @room'
ROOM_ALIAS = 'w5-row258-second-food-group'

class HmdpMeituanElementXBookmarkedStoreJishengkePollTask(BaseTask):
    apps = {'HMDP', 'Meituan', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    hmdp_user = HmdpUserAsset(phone=HMDP_LOGIN_PHONE, password=HMDP_LOGIN_PASSWORD, nick_name=HMDP_LOGIN_NICKNAME, city='Austin', level=1)
    seeded_favorite = HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name='Maple Leaf Bar')
    meituan_user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password='123456', user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name='Office Receiver', phone='5550101053', address='Office', address_detail='Room 258', label='Office', gender='male', city=MEITUAN_LOGIN_CITY)
    expected_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name='Jishengke', foods=[MeituanOrderFood(food_name='Mexican chicken rolls', quantity=3)], status='Payment successful', address_name='Office Receiver', code=200, delivery_status=1)
    member = ElementXUserAsset(username='w5-row258-member', password='password', display_name='Second Food Member')
    room = ElementXRoomAsset(name='Second Food Group', room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row258-member'], alias_localpart=ROOM_ALIAS, topic='Food poll')
    assets = (hmdp_user, seeded_favorite, meituan_user, address, member, room)

    goal = (
        'Open HMDP and identify your first bookmarked store for your final response. Then open Meituan and order three "Mexican chicken rolls" from Jishengke using the Office address and pay with Alipay. '
        'Open ElementX, send a room-mentioned message in Second Food Group using exactly this format: "<first bookmarked HMDP store> is the first bookmarked store. @room", and create a poll titled "What else would everyone like to eat?" with two options: the actual name of the first bookmarked HMDP store, and Jishengke. '
        'After finishing those actions, answer in exactly this format: "First bookmarked HMDP store: <store name>.".'
    )

    def criteria(self):
        return [
            AnswerEquals(ANSWER),
            AssetExists(self.expected_order, task=self),
            AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=COMMENT, mentions_room=True), task=self),
            AssetExists(ElementXPollAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', question='What else would everyone like to eat?', options=['Maple Leaf Bar', 'Jishengke']), task=self),
        ]
