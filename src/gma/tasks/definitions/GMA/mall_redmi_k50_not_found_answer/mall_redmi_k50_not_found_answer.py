from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallCartItemAsset, MallMemberAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


PRODUCT_SN = "1258669"


class MallRedmiK50NotFoundAnswerTask(BaseTask):
    apps = {"Mall"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent reports that Redmi K50 standard version is not found and asks what to do, "
        "answer exactly: Add one HUAWEI Mate 80 Pro default Mall listing to the cart instead; I have no color or storage preference. Do not answer unrelated questions."
    )
    assets = (
        MallMemberAsset(
            username=MALL_LOGIN_USERNAME,
            password="123456",
            nickname=MALL_LOGIN_NICKNAME,
            phone=MALL_LOGIN_PHONE,
            city=MALL_LOGIN_CITY,
            status=1,
        ),
    )
    goal = "Open Mall and add the Redmi K50 standard version to my favorites."

    def criteria(self):
        return [AssetExists(MallCartItemAsset(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, quantity=1, delete_status=False), task=self)]
