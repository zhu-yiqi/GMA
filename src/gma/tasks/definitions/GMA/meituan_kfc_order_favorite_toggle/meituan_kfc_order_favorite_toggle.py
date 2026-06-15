
from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanCollectionAsset, MeituanOrderAsset, MeituanOrderFood, MeituanSessionAsset, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ADDRESS_NAME = "Company"
RESTAURANT = "KFC"


class MeituanKfcOrderFavoriteToggleTask(BaseTask):
    apps = {"Meituan"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    session = MeituanSessionAsset(username=MEITUAN_LOGIN_USERNAME, password="123456")
    address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name=ADDRESS_NAME, phone="5550101095", address="Company Campus", address_detail="Building B Desk", label="Office", gender="male", province="New York State", city=MEITUAN_LOGIN_CITY)
    expected_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=RESTAURANT, foods=[MeituanOrderFood(food_name="Classic signature breakfast three-piece set", quantity=1), MeituanOrderFood(food_name="Pork fillet panini 2-piece set", quantity=1)], status="Payment successful", address_name=ADDRESS_NAME, code=200, delivery_status=1)
    expected_favorite = MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=RESTAURANT)
    assets = (user, session, address)

    goal = (
        "Open Meituan, go to Nearby Restaurant, use the Top Rate list, and open \"KFC\". "
        "Order one \"Classic signature breakfast three-piece set\" and one \"Pork fillet panini 2-piece set\" using the saved Company address and pay with Alipay. "
        "The store is not already favorited, so favorite it."
    )

    def criteria(self):
        return [AssetExists(self.expected_order, task=self), AssetExists(self.expected_favorite, task=self)]
