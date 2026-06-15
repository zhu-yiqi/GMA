from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanUserAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


class MeituanDeleteMikeDeliveryAddressTask(BaseTask):
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
        name="Mike",
        phone="5550101098",
        address="North Campus Gate",
        address_detail="Room 303",
        label="Home",
        province="Asset State",
        city=MEITUAN_LOGIN_CITY,
    )
    assets = (login_user, seeded_address)

    goal = 'Open Meituan and delete the delivery address for "Mike" with phone number "5550101098".'

    def criteria(self):
        return [AssetDeleted(self.seeded_address, task=self)]
