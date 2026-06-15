from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallAddressAsset, MallMemberAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class MallAddDefaultManhattanAddressTask(BaseTask):
    apps = {"Mall"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = MallMemberAsset(
        username=MALL_LOGIN_USERNAME,
        password="123456",
        nickname=MALL_LOGIN_NICKNAME,
        phone=MALL_LOGIN_PHONE,
        city=MALL_LOGIN_CITY,
        status=1,
    )
    expected_address = MallAddressAsset(
        member_username=MALL_LOGIN_USERNAME,
        name="Dylan Harris",
        phone_number="5550101062",
        province="New York State",
        city="New York City",
        region="Manhattan Borough",
        detail_address="81 Madison Avenue",
        post_code="100000",
        default_status=True,
    )
    assets = (login_user,)

    goal = (
        "Open Mall and add a new default shipping address. Use receiver Dylan Harris, "
        "phone 5550101062, postal code 100000, region New York State, New York City, "
        "Manhattan Borough, and detail address 81 Madison Avenue."
    )

    def criteria(self):
        return [AssetExists(self.expected_address, task=self)]
