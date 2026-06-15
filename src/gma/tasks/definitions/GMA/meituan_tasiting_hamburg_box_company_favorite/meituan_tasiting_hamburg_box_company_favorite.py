
from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanCollectionAsset, MeituanOrderAsset, MeituanOrderFood, MeituanSessionAsset, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ADDRESS_NAME = "Company"
RESTAURANT = "TASITING"
ITEM = "Hamburg snack box set"


class MeituanTasitingHamburgBoxCompanyFavoriteTask(BaseTask):
    apps = {"Meituan"}
    difficulty = "medium"
    category = ['Information-Gathering Tasks']
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent says there is no delivery address or asks for delivery address information, answer exactly: "
        "Create a new Office-labeled delivery address with recipient Company, phone number 5550101093, "
        "street Company Campus, apartment Building C Desk, and use it for the order and pay with Alipay. "
        "Do not answer unrelated questions."
    )

    user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    session = MeituanSessionAsset(username=MEITUAN_LOGIN_USERNAME, password="123456")
    address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name=ADDRESS_NAME, phone="5550101093", address="Company Campus", address_detail="Building C Desk", label="Office", gender="male", province="New York State", city=MEITUAN_LOGIN_CITY)
    expected_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=RESTAURANT, foods=[MeituanOrderFood(food_name=ITEM, quantity=1)], status="Payment successful", address_name=ADDRESS_NAME, code=200, delivery_status=1)
    expected_favorite = MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=RESTAURANT)
    assets = (user, session)

    goal = (
        "Open Meituan, open \"TASITING\", add \"Hamburg snack box set\" to the cart, place the order, pay with Alipay, and favorite TASITING."
    )

    def criteria(self):
        return [AssetExists(self.address, task=self), AssetExists(self.expected_order, task=self), AssetExists(self.expected_favorite, task=self)]
