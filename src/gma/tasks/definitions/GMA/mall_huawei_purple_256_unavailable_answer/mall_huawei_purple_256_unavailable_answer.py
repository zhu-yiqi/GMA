from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallMemberAsset
from gma.tasks.base import BaseTask
from gma.tasks.definitions.tests.mall._criteria import MallProductFavorited


PRODUCT_NAME = "HUAWEI Mate 80 Pro"
PRODUCT_SN = "1258669"


class MallHuaweiPurple256UnavailableAnswerTask(BaseTask):
    apps = {"Mall"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent reports that the exact purple 256GB HUAWEI variant is unavailable and asks what to do, "
        "answer exactly: Favorite HUAWEI Mate 80 Pro instead; I only want the default Mall listing, with no color or storage preference. Do not answer unrelated questions."
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
    goal = "Open Mall and buy the first HUAWEI phone in purple with 256GB storage."

    def criteria(self):
        return [MallProductFavorited(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, product_name=PRODUCT_NAME)]
