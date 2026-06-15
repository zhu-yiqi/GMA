from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ContactAsset, MallMemberAsset, SmsMessageAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask
from gma.tasks.definitions.tests.mall._criteria import MallProductFavorited


PRODUCT_SN = "JNW6WYGVKF"
AUTHOR_ID = "w4-row229-phone-author"
CARTER_CONTACT = ContactAsset(name="Carter", phone_number="+15552290229")
INBOX = SmsMessageAsset(address=CARTER_CONTACT.phone_number, body="Please check Apple phones. I heard the iPhone 17 Pro is worth saving.", box="inbox", read=False, timestamp_ms=202610011000)
POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="iPhone 17 Pro Recommendation", content="Netizens recommend the iPhone 17 Pro model this week.", category="Technology", tags=["Apple", "iPhone 17 Pro"], image_urls=["/assets/messages-phone-brand-xsl-mall-favorite-iphone.png"], min_image_count=1, created_at_ms=1790845200000)
COLLECTION = XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POST.title, post_author_user_id=AUTHOR_ID)

class MessagesPhoneBrandXslMallFavoriteTask(BaseTask):
    apps = {"Messages", "XiaoShiLiu", "Mall"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        CARTER_CONTACT,
        INBOX,
        XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Phone Model Desk", email="phone.model.desk@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR),
        POST,
        MallMemberAsset(username=MALL_LOGIN_USERNAME, password="123456", nickname=MALL_LOGIN_NICKNAME, phone=MALL_LOGIN_PHONE, city=MALL_LOGIN_CITY, status=1),
    )
    goal = (
        "Open Messages and read Carter's SMS to get the phone brand and model. "
        "Then open XiaoShiLiu, search for that model, and save the recommendation note. Finally open Mall, find the matching phone product, and favorite the first matching product."
    )

    def criteria(self):
        return [
            AssetExists(COLLECTION, task=self),
            MallProductFavorited(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, product_name="iPhone 17 Pro"),
        ]
