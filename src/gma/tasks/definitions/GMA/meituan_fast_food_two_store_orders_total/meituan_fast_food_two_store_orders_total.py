
from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanCollectionAsset, MeituanOrderAsset, MeituanOrderFood, MeituanSessionAsset, MeituanUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


ADDRESS_NAME = "Default Fast Food"
TOTAL = "203.61"


class MeituanFastFoodTwoStoreOrdersTotalTask(BaseTask):
    apps = {"Meituan"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    session = MeituanSessionAsset(username=MEITUAN_LOGIN_USERNAME, password="123456")
    address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name=ADDRESS_NAME, phone="5550101083", address="Fast Food Address", address_detail="Room 331", label="Home", gender="male", province="New York State", city=MEITUAN_LOGIN_CITY)
    kfc_favorite = MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="KFC")
    mcd_favorite = MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="McDonald's")
    kfc_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="KFC", foods=[MeituanOrderFood(food_name="Three-piece hamburger set for one person", quantity=1), MeituanOrderFood(food_name="in Course Selection at Will OK Three-Piece Set", quantity=1), MeituanOrderFood(food_name="Hamburg set of five for one person.", quantity=1)], status="Payment successful", address_name=ADDRESS_NAME, code=200, delivery_status=1)
    mcd_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="McDonald's", foods=[MeituanOrderFood(food_name="French fries trio", quantity=1), MeituanOrderFood(food_name="Mai la Ji tui Bao single meal", quantity=1), MeituanOrderFood(food_name="Maiba classic three-person meal", quantity=1)], status="Payment successful", address_name=ADDRESS_NAME, code=200, delivery_status=1)
    assets = (user, session, address)

    goal = (
        "Open Meituan, favorite KFC and McDonald's, then place one order from KFC with the first three listed menu items. "
        "Place another order from McDonald's with the first three listed menu items. Use the default address and pay with Alipay for both orders. "
        "After placing both orders, calculate the combined total item price for all ordered items, excluding delivery fees, and answer with that total as a number with two decimal places."
    )

    def criteria(self):
        return [AssetExists(self.kfc_favorite, task=self), AssetExists(self.mcd_favorite, task=self), AssetExists(self.kfc_order, task=self), AssetExists(self.mcd_order, task=self), AnswerEquals(TOTAL)]
