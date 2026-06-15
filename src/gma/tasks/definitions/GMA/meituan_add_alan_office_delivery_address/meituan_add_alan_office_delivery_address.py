from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class MeituanAddAlanOfficeDeliveryAddressTask(BaseTask):
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
    expected_address = MeituanAddressAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        name="Alan New account",
        phone="5550101080",
        address="Northwood Campus",
        address_detail="Rm 666",
        label="Office",
        province="Asset State",
        city=MEITUAN_LOGIN_CITY,
    )
    assets = (login_user,)

    goal = (
        'Open Meituan and add a new delivery address with recipient "Alan New account", '
        'phone number "5550101080", street "Northwood Campus", apartment "Rm 666", and label "Office".'
    )

    def criteria(self):
        return [AssetExists(self.expected_address, task=self)]
