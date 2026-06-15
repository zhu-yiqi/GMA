from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallMemberAsset, MallOrderAsset, MallOrderItem
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


PRODUCT_NAME = "55-inch class Samsung The Serif art TV LS01DB"
PRODUCT_SN = "QA55LS01DBJXXZ"
ORDER_SN = "W1-MALL-CONFIRM-TV-001"


class MallConfirmReceiptSamsungTvOrderTask(BaseTask):
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
    before_order = MallOrderAsset(
        order_sn=ORDER_SN,
        member_username=MALL_LOGIN_USERNAME,
        items=[MallOrderItem(product_sn=PRODUCT_SN, quantity=1)],
        status=2,
        receiver_name="Jordan TV Receiver",
        receiver_phone="5550101073",
        receiver_province="New York State",
        receiver_city="New York City",
        receiver_region="Manhattan Borough",
        receiver_detail_address="TV Receipt Room 12",
        created_at_ms=1790809200000,
    )
    after_order = MallOrderAsset(
        order_sn=ORDER_SN,
        member_username=MALL_LOGIN_USERNAME,
        items=[MallOrderItem(product_sn=PRODUCT_SN, quantity=1)],
        status=3,
        receiver_name="Jordan TV Receiver",
        receiver_phone="5550101073",
        receiver_province="New York State",
        receiver_city="New York City",
        receiver_region="Manhattan Borough",
        receiver_detail_address="TV Receipt Room 12",
        created_at_ms=1790809200000,
    )
    assets = (login_user, before_order)

    goal = (
        f"Open Mall and confirm receipt for my purchased television, {PRODUCT_NAME}, "
        "so the order becomes completed."
    )

    def criteria(self):
        return [AssetModified(self.before_order, self.after_order, task=self)]
