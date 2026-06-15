from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import ContactAsset, MeituanCollectionAsset, MeituanUserAsset, SmsMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

FOOD_STORE = "ZHANGLIANG SPICY HOTPOT"
SUPERMARKET_STORE = "Huiwang lifestyle supermarket"
FRESH_STORE = "Bai orchard"
CONTACT = ContactAsset(name="Alex Parker", phone_number="+15552110211")
MESSAGE = "I have bookmarked my favorite stores on Meituan. The store names are as follows: First: ZHANGLIANG SPICY HOTPOT; Second: Huiwang lifestyle supermarket; Third: Bai orchard."
EXPECTED_SMS = SmsMessageAsset(address=CONTACT.phone_number, body=MESSAGE, box="sent", read=True)


class MeituanThreeStoreFavoritesMessageTask(BaseTask):
    apps = {"Meituan", "Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1),
        CONTACT,
    )
    goal = (
        "Open Meituan and bookmark these three stores: ZHANGLIANG SPICY HOTPOT, Huiwang lifestyle supermarket, "
        "and Bai orchard. Then open Messages and send Alex Parker this exact message: "
        "\"I have bookmarked my favorite stores on Meituan. The store names are as follows: First: ZHANGLIANG SPICY HOTPOT; Second: Huiwang lifestyle supermarket; Third: Bai orchard.\""
    )

    def criteria(self):
        return [
            AssetExists(MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=FOOD_STORE), task=self),
            AssetExists(MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=SUPERMARKET_STORE), task=self),
            AssetExists(MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=FRESH_STORE), task=self),
            AssetExists(EXPECTED_SMS, task=self),
        ]
