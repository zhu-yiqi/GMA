from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallCartItemAsset, MallMemberAsset
from gma.evaluation import AssetExists, AssetMissing
from gma.tasks.base import BaseTask


KEEP_PRODUCT_NAME = "HUAWEI Mate 80 Pro"
KEEP_PRODUCT_SN = "1258669"
REMOVE_PRODUCT_NAME = "HUAWEI Mate XTs Ultimate Design"
REMOVE_PRODUCT_SN = "48796328"


class MallRemoveHuaweiMateXtsFromCartTask(BaseTask):
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
    keep_cart_item = MallCartItemAsset(
        member_username=MALL_LOGIN_USERNAME,
        product_sn=KEEP_PRODUCT_SN,
        quantity=1,
    )
    remove_cart_item = MallCartItemAsset(
        member_username=MALL_LOGIN_USERNAME,
        product_sn=REMOVE_PRODUCT_SN,
        quantity=1,
    )
    assets = (login_user, keep_cart_item, remove_cart_item)

    goal = (
        "Open the Mall shopping cart and remove HUAWEI Mate XTs Ultimate Design from the cart. "
        "Leave HUAWEI Mate 80 Pro in the cart."
    )

    def criteria(self):
        return [
            AssetMissing(self.remove_cart_item, task=self),
            AssetExists(self.keep_cart_item, task=self),
        ]
