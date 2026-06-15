
from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanCollectionAsset, MeituanOrderAsset, MeituanOrderFood, MeituanSessionAsset, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ADDRESS_NAME = "Fresh Default"


class MeituanAfternoonFavoritesFreshOrderTask(BaseTask):
    apps = {"Meituan"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    session = MeituanSessionAsset(username=MEITUAN_LOGIN_USERNAME, password="123456")
    address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name=ADDRESS_NAME, phone="5550101081", address="78 Oak Street", address_detail="Apartment 351", label="Home", gender="male", province="New York State", city=MEITUAN_LOGIN_CITY)
    favorites = (MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="Rural Malong"), MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="Blue Frog"), MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="PARTICLE COFFEE"))
    expected_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="Rural Malong", foods=[MeituanOrderFood(food_name="Tomahawk Steak", quantity=1)], status="Payment successful", address_name=ADDRESS_NAME, code=200, delivery_status=1)
    assets = (user, session, address)

    goal = (
        "Open Meituan, go to the Afternoon Tea section, sort by Nearest, and favorite the first three stores shown. Then open the top store from that sorted list, add \"Tomahawk Steak\" to the cart, and place the order using the default address and pay with Alipay."
    )

    def criteria(self):
        return [*[AssetExists(item, task=self) for item in self.favorites], AssetExists(self.expected_order, task=self)]
