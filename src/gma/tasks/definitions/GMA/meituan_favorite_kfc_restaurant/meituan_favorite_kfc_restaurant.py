from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanCollectionAsset, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class MeituanFavoriteKfcRestaurantTask(BaseTask):
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
    expected_collection = MeituanCollectionAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name="KFC",
    )
    assets = (login_user,)

    goal = 'Open Meituan, find the restaurant "KFC", and add it to favorites.'

    def criteria(self):
        return [AssetExists(self.expected_collection, task=self)]
