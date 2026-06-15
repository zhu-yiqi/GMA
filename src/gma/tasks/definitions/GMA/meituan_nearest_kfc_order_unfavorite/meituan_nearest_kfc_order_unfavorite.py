from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import (
    MeituanAddressAsset,
    MeituanCollectionAsset,
    MeituanOrderAsset,
    MeituanOrderFood,
    MeituanUserAsset,
)
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


KFC = "KFC"
KFC_ITEMS = (
    "Three-piece hamburger set for one person",
    "in Course Selection at Will OK Three-Piece Set",
    "Hamburg set of five for one person.",
)
MIKE_ADDRESS = "Mike"


class MeituanNearestKfcOrderUnfavoriteTask(BaseTask):
    apps = {"Meituan"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    login_user = MeituanUserAsset(
        username=MEITUAN_LOGIN_USERNAME,
        password="123456",
        user_id=MEITUAN_LOGIN_USER_ID,
        status=1,
    )
    mike_home = MeituanAddressAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        name=MIKE_ADDRESS,
        phone="5550101087",
        address="Mike Home Tower",
        address_detail="Room 1201",
        label="Home",
        gender="male",
        city="Seattle",
    )
    spare_home = MeituanAddressAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        name="Jordan",
        phone="5550101088",
        address="Jordan Home Court",
        address_detail="Unit 3B",
        label="Home",
        gender="male",
        city="Seattle",
    )
    seeded_favorite = MeituanCollectionAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name=KFC,
    )
    expected_order = MeituanOrderAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name=KFC,
        foods=tuple(MeituanOrderFood(food_name=name, quantity=1) for name in KFC_ITEMS),
        status="Payment successful",
        address_name=MIKE_ADDRESS,
        code=200,
        delivery_status=1,
    )
    assets = (login_user, mike_home, spare_home, seeded_favorite)

    goal = (
        "Open Meituan. In Nearby Restaurant, use the Nearest list and open the KFC store. "
        "Order these first three menu items together: Three-piece hamburger set for one person; "
        "in Course Selection at Will OK Three-Piece Set; Hamburg set of five for one person. "
        "If more than one Home address is shown, use the Home address named Mike, pay with Alipay, "
        "and then remove KFC from favorites."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_order, task=self),
            AssetDeleted(self.seeded_favorite, task=self),
        ]
