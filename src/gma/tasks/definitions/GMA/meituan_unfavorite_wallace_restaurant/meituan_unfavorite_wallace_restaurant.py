from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MeituanCollectionAsset, MeituanUserAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


class MeituanUnfavoriteWallaceRestaurantTask(BaseTask):
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
    seeded_collection = MeituanCollectionAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name="Wallace",
    )
    assets = (login_user, seeded_collection)

    goal = 'Open Meituan and remove "Wallace" from my favorited restaurants.'

    def criteria(self):
        return [AssetDeleted(self.seeded_collection, task=self)]
