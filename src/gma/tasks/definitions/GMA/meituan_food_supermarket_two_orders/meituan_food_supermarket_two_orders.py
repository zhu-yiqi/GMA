
from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanOrderAsset, MeituanOrderFood, MeituanSessionAsset, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ADDRESS_NAME = "Order Default"


class MeituanFoodSupermarketTwoOrdersTask(BaseTask):
    apps = {"Meituan"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    session = MeituanSessionAsset(username=MEITUAN_LOGIN_USERNAME, password="123456")
    address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name=ADDRESS_NAME, phone="5550101084", address="45 Pine Street", address_detail="Apartment 361", label="Home", gender="male", province="New York State", city=MEITUAN_LOGIN_CITY)
    food_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="Three Squirrels", foods=[MeituanOrderFood(food_name="Milk-scented Hand-Torn Bread", quantity=3)], status="Payment successful", address_name=ADDRESS_NAME, code=200, delivery_status=1)
    supermarket_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="Xiaolan Life Premium Supermarket", foods=[MeituanOrderFood(food_name="Royal Canin Cat Food", quantity=1)], status="Payment successful", address_name=ADDRESS_NAME, code=200, delivery_status=1)
    assets = (user, session, address)

    goal = (
        "Open Meituan and place two separate orders using the default address and pay with Alipay for both orders. First, go to Food, open Three Squirrels, and order 3 Milk-scented Hand-Torn Bread. Then go to Supermarket, open Xiaolan Life Premium Supermarket, and order 1 Royal Canin Cat Food."
    )

    def criteria(self):
        return [AssetExists(self.food_order, task=self), AssetExists(self.supermarket_order, task=self)]
