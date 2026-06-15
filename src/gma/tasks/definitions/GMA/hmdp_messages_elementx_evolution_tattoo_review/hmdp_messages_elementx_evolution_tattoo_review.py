from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import ContactAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, HmdpShopFavoriteAsset, HmdpShopReviewAsset, HmdpUserAsset, SmsMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

SHOP = 'Evolution Tattoo'
FIRST_COMMENT = 'Clean space and friendly staff.'
SMS_TEXT = "Let's go to this store for dinner at 6 PM; please confirm upon receipt"
GROUP_TEXT = f"Anyone up for dinner together? I found the store's reviews quite good-the first comment reads: {FIRST_COMMENT}"
ROOM_ALIAS = 'eat'

class HmdpMessagesElementXEvolutionTattooReviewTask(BaseTask):
    apps = {'HMDP', 'Messages', 'Contacts', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    hmdp_user = HmdpUserAsset(phone=HMDP_LOGIN_PHONE, password=HMDP_LOGIN_PASSWORD, nick_name=HMDP_LOGIN_NICKNAME, city='Austin', level=1)
    seeded_review = HmdpShopReviewAsset(user_phone='5550101054', shop_name=SHOP, content=FIRST_COMMENT, score=5)
    contact = ContactAsset(name='oliver_stone', phone_number='+15552012560')
    member = ElementXUserAsset(username='w5-row256-eat-member', password='password', display_name='Eat Group Member')
    room = ElementXRoomAsset(name='eat', room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row256-eat-member'], alias_localpart=ROOM_ALIAS, topic='Dinner plans')
    expected_sms = SmsMessageAsset(address=contact.phone_number, body=SMS_TEXT, box='sent', read=True)
    assets = (hmdp_user, seeded_review, contact, member, room)

    goal = (
        'Open HMDP, search for "Evolution Tattoo", favorite it, and record the first review comment. '
        'Open Messages and send oliver_stone exactly "Let\'s go to this store for dinner at 6 PM; please confirm upon receipt". '
        'Then open ElementX, go to the eat group, and send a message in exactly this format: "Anyone up for dinner together? I found the store\'s reviews quite good-the first comment reads: <first review comment>".'
    )

    def criteria(self):
        return [
            AssetExists(HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=SHOP), task=self),
            AssetExists(self.expected_sms, task=self),
            AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=GROUP_TEXT), task=self),
        ]
