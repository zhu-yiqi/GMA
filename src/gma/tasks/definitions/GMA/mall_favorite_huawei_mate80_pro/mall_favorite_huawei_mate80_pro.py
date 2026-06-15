from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallMemberAsset
from gma.tasks.base import BaseTask
from gma.tasks.definitions.tests.mall._criteria import MallProductFavorited


PRODUCT_NAME = "HUAWEI Mate 80 Pro"
PRODUCT_SN = "1258669"


class MallFavoriteHuaweiMate80ProTask(BaseTask):
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
    assets = (login_user,)

    goal = (
        "Open Mall, browse the HUAWEI brand, and favorite HUAWEI Mate 80 Pro, "
        "the first HUAWEI product in the seeded catalog."
    )

    def criteria(self):
        return [
            MallProductFavorited(
                member_username=MALL_LOGIN_USERNAME,
                product_sn=PRODUCT_SN,
                product_name=PRODUCT_NAME,
            )
        ]
