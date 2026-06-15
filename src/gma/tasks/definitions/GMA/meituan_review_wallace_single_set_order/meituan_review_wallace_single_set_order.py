from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanCommentAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


RESTAURANT = "Wallace"
FOOD = "Single set of 5 pieces"
ORDER_ID = 10058
ADDRESS_NAME = "Jordan Wallace"


class MeituanReviewWallaceSingleSetOrderTask(BaseTask):
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
        phone="5550101092",
        address="Campus Food Court",
        address_detail="Room 058",
        label="Office",
        province="New York State",
        city=MEITUAN_LOGIN_CITY,
    )
    seeded_order = MeituanOrderAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name=RESTAURANT,
        foods=[MeituanOrderFood(food_name=FOOD, quantity=1)],
        status="Paid",
        address_name=ADDRESS_NAME,
        order_id=ORDER_ID,
        code=200,
        delivery_status=4,
        has_comment=False,
    )
    expected_comment = MeituanCommentAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        user_name=MEITUAN_LOGIN_USERNAME,
        restaurant_name=RESTAURANT,
        content="Tasted good!",
        food_score=5,
        delivery_score=5,
        order_id=ORDER_ID,
    )
    assets = (login_user, seeded_address, seeded_order)

    goal = (
        'Open Meituan and review the completed "Single set of 5 pieces" order from Wallace. '
        'Give both the store and delivery rider 5 stars, and write exactly "Tasted good!"'
    )

    def criteria(self):
        return [AssetExists(self.expected_comment, task=self)]
