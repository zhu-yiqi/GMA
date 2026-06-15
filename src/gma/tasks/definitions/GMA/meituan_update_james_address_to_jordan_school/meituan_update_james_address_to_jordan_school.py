from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanAddressAsset, MeituanUserAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


class MeituanUpdateJamesAddressToJordanSchoolTask(BaseTask):
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
    before_address = MeituanAddressAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        name="James",
        phone="5550101097",
        address="Campus Library",
        address_detail="Room 101",
        label="Home",
        province="Asset State",
        city=MEITUAN_LOGIN_CITY,
    )
    after_address = MeituanAddressAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        name="Jordan",
        phone="5550101097",
        address="Campus Library",
        address_detail="Room 101",
        label="School",
        province="Asset State",
        city=MEITUAN_LOGIN_CITY,
    )
    assets = (login_user, before_address)

    goal = (
        'Open Meituan and edit the delivery address for "James" with phone number '
        '"5550101097". Change the recipient name to "Jordan", keep the phone number, '
        'and set the address label to "School".'
    )

    def criteria(self):
        return [AssetModified(self.before_address, self.after_address, task=self)]
