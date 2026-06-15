
from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanOrderAsset, MeituanOrderFood, MeituanSessionAsset, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ADDRESS_NAME = "KFC Default"


class MeituanKfcReorderRecommendBreakfastTask(BaseTask):
    apps = {"Meituan"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    session = MeituanSessionAsset(username=MEITUAN_LOGIN_USERNAME, password="123456")
    address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name=ADDRESS_NAME, phone="5550101086", address="120 Maple Avenue", address_detail="Apartment 341", label="Home", gender="male", province="New York State", city=MEITUAN_LOGIN_CITY)
    history_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="KFC", foods=[MeituanOrderFood(food_name="Three-piece hamburger set for one person", quantity=1)], status="Payment successful", address_name=ADDRESS_NAME, code=200, delivery_status=1, created_at_ms=202609300900)
    expected_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="KFC", foods=[MeituanOrderFood(food_name="Three-piece hamburger set for one person", quantity=1), MeituanOrderFood(food_name="Hamburg set of five for one person.", quantity=1), MeituanOrderFood(food_name="Classic signature breakfast three-piece set", quantity=1), MeituanOrderFood(food_name="Pork fillet panini 2-piece set", quantity=1)], status="Payment successful", address_name=ADDRESS_NAME, code=200, delivery_status=1)
    assets = (user, session, address, history_order)

    goal = (
        "Open Meituan, locate the existing KFC order, and place another KFC order that includes the same item from that existing order. Also add the third Recommend item \"Hamburg set of five for one person.\" and the first two Breakfast items \"Classic signature breakfast three-piece set\" and \"Pork fillet panini 2-piece set\", one of each. Use the default address and pay with Alipay."
    )

    def criteria(self):
        return [AssetExists(self.expected_order, task=self)]
