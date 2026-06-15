from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


RESTAURANT = "McDonald's"
FIRST_ITEM = "French fries trio"
SECOND_ITEM = "Mai la Ji tui Bao single meal"
ADDRESS_NAME = "Jordan Miller"


class MeituanOrderFirstTwoMcdonaldsItemsTask(BaseTask):
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
        phone="5550101090",
        address="Campus Food Court",
        address_detail="Room 057",
        label="Office",
        province="Asset State",
        city=MEITUAN_LOGIN_CITY,
    )
    expected_order = MeituanOrderAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name=RESTAURANT,
        foods=[
            MeituanOrderFood(food_name=FIRST_ITEM, quantity=1),
            MeituanOrderFood(food_name=SECOND_ITEM, quantity=1),
        ],
        status="Payment successful",
        address_name=ADDRESS_NAME,
        code=200,
        delivery_status=1,
    )
    assets = (login_user, seeded_address)

    goal = (
        'Open Meituan, find "McDonald\'s", add the first two menu items to the cart '
        'with quantity one each, place the order using the saved address "Jordan Miller", '
        'and pay with Alipay.'
    )

    def criteria(self):
        return [AssetExists(self.expected_order, task=self)]
