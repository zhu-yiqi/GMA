from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallAddressAsset, MallMemberAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


OLD_SHANGHAI = MallAddressAsset(
    member_username=MALL_LOGIN_USERNAME,
    name="Chicago Receiver",
    phone_number="5550101063",
    province="Chicago City",
    city="Chicago City",
    region="River North District",
    detail_address="Old Chicago Address Apartment 8",
    post_code="200120",
    default_status=False,
)
UPDATED_SHANGHAI = MallAddressAsset(
    member_username=MALL_LOGIN_USERNAME,
    name="Quinn Foster",
    phone_number="5550101064",
    province="Chicago City",
    city="Chicago City",
    region="River North District",
    detail_address="25 Michigan Avenue",
    post_code="200120",
    default_status=False,
)
NEW_GUANGZHOU = MallAddressAsset(
    member_username=MALL_LOGIN_USERNAME,
    name="Sam Foster",
    phone_number="5550101065",
    province="California State",
    city="San Francisco City",
    region="Mission District",
    detail_address="22 Market Street, Bayview Apartments",
    post_code="120000",
    default_status=True,
)


class MallAddDefaultSanFranciscoUpdateChicagoAddressTask(BaseTask):
    apps = {"Mall"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        MallMemberAsset(
            username=MALL_LOGIN_USERNAME,
            password="123456",
            nickname=MALL_LOGIN_NICKNAME,
            phone=MALL_LOGIN_PHONE,
            city=MALL_LOGIN_CITY,
            status=1,
        ),
        OLD_SHANGHAI,
    )
    goal = (
        "In Mall, add a shipping address with recipient Sam Foster, phone 5550101065, "
        "postal code 120000, region California State, San Francisco City, Mission District, and detail address 22 Market Street, "
        "Bayview Apartments. Set it as the default address. Then update the saved Chicago "
        "address so the recipient is Quinn Foster, the phone is 5550101064, and the detail address "
        "is 25 Michigan Avenue."
    )

    def criteria(self):
        return [
            AssetExists(NEW_GUANGZHOU, task=self),
            AssetModified(OLD_SHANGHAI, UPDATED_SHANGHAI, task=self),
        ]
