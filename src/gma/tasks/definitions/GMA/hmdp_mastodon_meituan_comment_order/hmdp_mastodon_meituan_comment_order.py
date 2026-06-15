from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import HmdpBlogAsset, HmdpBlogCommentAsset, HmdpFollowAsset, HmdpUserAsset, MastodonFavoriteAsset, MastodonStatusAsset, MeituanAddressAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

COMMENT = 'This shop has a calm atmosphere and quick service.'
BLOG_TIME_MS = 1790848800000

class HmdpMastodonMeituanCommentOrderTask(BaseTask):
    apps = {'HMDP', 'Mastodon', 'Meituan'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    login = HmdpUserAsset(phone=HMDP_LOGIN_PHONE, password=HMDP_LOGIN_PASSWORD, nick_name=HMDP_LOGIN_NICKNAME, city='Austin', level=1)
    author = HmdpUserAsset(phone='5550101051', password='123456', nick_name='Review Author Riley', city='Austin')
    blog = HmdpBlogAsset(author_phone='5550101051', shop_name='Maple Leaf Bar', title='First Note With Comment', content='A short note for the first-comment workflow.', images=['/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg'], liked=9999, created_at_ms=BLOG_TIME_MS)
    comment = HmdpBlogCommentAsset(blog_title='First Note With Comment', blog_author_phone='5550101051', author_phone='5550101051', content=COMMENT, created_at_ms=BLOG_TIME_MS + 1000)
    meituan_user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password='123456', user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name='Order Receiver', phone='5550101052', address='Order Office', address_detail='Room 260', label='Office', gender='male', city=MEITUAN_LOGIN_CITY)
    expected_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name='Jishengke', foods=[MeituanOrderFood(food_name='Zinger burger', quantity=3)], status='Payment successful', address_name='Order Receiver', code=200, delivery_status=1)
    assets = (login, author, blog, comment, meituan_user, address)

    goal = (
        'Open HMDP, open the first note with a comment, read that first comment, and follow the comment author. '
        'Open Mastodon, create a public post whose text is exactly the comment you read, then favorite your new post. '
        'Then open Meituan and order three "Zinger burger" items from Jishengke using the Order Office address and pay with Alipay.'
    )

    def criteria(self):
        return [
            AssetExists(HmdpFollowAsset(follower_phone=HMDP_LOGIN_PHONE, following_phone='5550101051'), task=self),
            AssetExists(MastodonStatusAsset(username='owner', text=COMMENT, visibility='public'), task=self),
            AssetExists(MastodonFavoriteAsset(actor_username='owner', target_username='owner', target_text=COMMENT), task=self),
            AssetExists(self.expected_order, task=self),
        ]
