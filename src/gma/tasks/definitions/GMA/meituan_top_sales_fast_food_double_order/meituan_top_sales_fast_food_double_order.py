from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


FIRST_TOP_SALES_RESTAURANT = "Tianlala fresh fruit cha"
SECOND_TOP_SALES_RESTAURANT = "Mixue Ice Cream & Tea"
DEFAULT_ADDRESS = "Owner Default"


class MeituanTopSalesFastFoodDoubleOrderTask(BaseTask):
    apps = {"Meituan"}
    difficulty = "hard"
    snapshot = "gma_ready_state"

    login_user = MeituanUserAsset(
        username=MEITUAN_LOGIN_USERNAME,
        password="123456",
        user_id=MEITUAN_LOGIN_USER_ID,
        status=1,
    )
    default_address = MeituanAddressAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        name=DEFAULT_ADDRESS,
        phone="5550101094",
        address="Owner Default Residence",
        address_detail="Suite 2102",
        label="Home",
        gender="male",
        city="Seattle",
    )
    first_order = MeituanOrderAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name=FIRST_TOP_SALES_RESTAURANT,
        foods=[MeituanOrderFood(food_name="Taihong lemon tea", quantity=2)],
        status="Payment successful",
        address_name=DEFAULT_ADDRESS,
        code=200,
        delivery_status=1,
    )
    second_order = MeituanOrderAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name=SECOND_TOP_SALES_RESTAURANT,
        foods=[MeituanOrderFood(food_name="Bang da xian orange", quantity=3)],
        status="Payment successful",
        address_name=DEFAULT_ADDRESS,
        code=200,
        delivery_status=1,
    )
    assets = (login_user, default_address)

    goal = (
        "Open Meituan, go to Fast Food, and sort by Top Sales. For each of the first two stores shown, "
        "find the cheapest menu item and order the fewest copies needed to meet that store's minimum order amount. "
        "Place the two orders separately using the default address and pay with Alipay for both orders."
    )

    def criteria(self):
        return [AssetExists(self.first_order, task=self), AssetExists(self.second_order, task=self)]
