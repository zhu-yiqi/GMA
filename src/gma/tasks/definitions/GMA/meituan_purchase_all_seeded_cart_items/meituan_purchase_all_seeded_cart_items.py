from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanCartItemAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


RESTAURANT = "KFC"
FOODS = [
    "Three-piece hamburger set for one person",
    "in Course Selection at Will OK Three-Piece Set",
    "Hamburg set of five for one person.",
]
ADDRESS_NAME = "Avery Brooks"


class MeituanPurchaseAllSeededCartItemsTask(BaseTask):
    apps = {"Meituan"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = MeituanUserAsset(
        username=MEITUAN_LOGIN_USERNAME,
        password="123456",
        user_id=MEITUAN_LOGIN_USER_ID,
        city=MEITUAN_LOGIN_CITY,
        status=1,
    )
    seeded_address = MeituanAddressAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        name=ADDRESS_NAME,
        phone="5550101091",
        address="Campus Food Court",
        address_detail="Room 059",
        label="Office",
        province="Asset State",
        city=MEITUAN_LOGIN_CITY,
    )
    cart_items = tuple(
        MeituanCartItemAsset(
            user_id=MEITUAN_LOGIN_USER_ID,
            restaurant_name=RESTAURANT,
            food_name=food,
            quantity=1,
        )
        for food in FOODS
    )
    expected_order = MeituanOrderAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name=RESTAURANT,
        foods=[MeituanOrderFood(food_name=food, quantity=1) for food in FOODS],
        status="Payment successful",
        address_name=ADDRESS_NAME,
        code=200,
        delivery_status=1,
    )
    assets = (login_user, seeded_address, *cart_items)

    goal = (
        'Open Meituan, go to the shopping cart, and purchase all items currently in the cart. '
        'Use the saved address "Avery Brooks" and pay with Alipay.'
    )

    def criteria(self):
        return [AssetExists(self.expected_order, task=self)]
