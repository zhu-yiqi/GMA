from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallAddressAsset, MallMemberAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


class MallUpdateBrooklynAddressToQueensTask(BaseTask):
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
    before_address = MallAddressAsset(
        member_username=MALL_LOGIN_USERNAME,
        name="Casey Reed",
        phone_number="5550101077",
        province="New York State",
        city="New York City",
        region="Brooklyn Borough",
        detail_address="Building 12, Morning Plaza",
        post_code="100020",
        default_status=False,
    )
    after_address = MallAddressAsset(
        member_username=MALL_LOGIN_USERNAME,
        name="Harper Brooks",
        phone_number="5550101077",
        province="New York State",
        city="New York City",
        region="Queens Borough",
        detail_address="Building 12, Morning Plaza",
        post_code="100020",
        default_status=False,
    )
    assets = (login_user, before_address)

    goal = (
        "Open Mall address manager and update the saved address currently in Brooklyn Borough. "
        "Change the receiver name to Harper Brooks and change the district/region to Queens Borough. "
        "Keep the phone number, province, city, postal code, and detail address unchanged."
    )

    def criteria(self):
        return [AssetModified(self.before_address, self.after_address, task=self)]
