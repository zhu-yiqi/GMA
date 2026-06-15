from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, HmdpShopFavoriteAsset, HmdpUserAsset, MastodonAccountAsset, MastodonBookmarkAsset, MastodonFollowAsset, MastodonPollSpec, MastodonPollStatusAsset, MastodonPollVoteAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

MAIN_USER = 'owner'
LEO = 'leo_row252'
POLL_TEXT = 'Nearby food poll from Leo.'
FOOD_SHOP = 'Maple Leaf Bar'
ROOM_ALIAS = 'w5-row252-food-spot-group'
MESSAGE = "Let's go check out the food spot together! @room"

class MastodonHmdpElementXFoodPollPlanTask(BaseTask):
    apps = {'Mastodon', 'HMDP', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    leo_account = MastodonAccountAsset(username=LEO, email='leo-row252@example.com', display_name='Leo Food Poll', bio='Seeded food poll account.')
    poll = MastodonPollStatusAsset(username=LEO, text=POLL_TEXT, visibility='public', poll=MastodonPollSpec(options=('Cafe', 'Noodle Shop', 'Dessert Bar'), multiple=False), created_at_ms=202610011000)
    hmdp_user = HmdpUserAsset(phone=HMDP_LOGIN_PHONE, password=HMDP_LOGIN_PASSWORD, nick_name=HMDP_LOGIN_NICKNAME, city='Austin', level=1)
    member = ElementXUserAsset(username='w5-row252-food-member', password='password', display_name='Food Spot Member')
    room = ElementXRoomAsset(name='Food Spot Group', room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row252-food-member'], alias_localpart=ROOM_ALIAS, topic='Food plans')
    assets = (leo_account, poll, hmdp_user, member, room)

    goal = (
        f'Open Mastodon, find Leo Food Poll, follow him, vote for "Noodle Shop" in the poll "{POLL_TEXT}", and bookmark that poll. '
        f'Then open HMDP and favorite "{FOOD_SHOP}". Open ElementX, go to the Food Spot Group room, and send exactly "{MESSAGE}" with a room-wide mention.'
    )

    def criteria(self):
        return [
            AssetExists(MastodonFollowAsset(follower_username=MAIN_USER, followed_username=LEO), task=self),
            AssetExists(MastodonPollVoteAsset(voter_username=MAIN_USER, poll_username=LEO, poll_text=POLL_TEXT, choices=('Noodle Shop',)), task=self),
            AssetExists(MastodonBookmarkAsset(actor_username=MAIN_USER, target_username=LEO, target_text=POLL_TEXT), task=self),
            AssetExists(HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=FOOD_SHOP), task=self),
            AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=MESSAGE, mentions_room=True), task=self),
        ]
