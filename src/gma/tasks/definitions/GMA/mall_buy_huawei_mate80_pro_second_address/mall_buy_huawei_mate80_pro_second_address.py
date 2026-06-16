from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallAddressAsset, MallMemberAsset
from gma.tasks.base import BaseTask
from gma.evaluation.checks.mall import MallCheckoutOrderCreated


PRODUCT_NAME = "HUAWEI Mate 80 Pro"
PRODUCT_SN = "1258669"
SECOND_RECEIVER = "Morgan Carter"


class MallBuyHuaweiMate80ProSecondAddressTask(BaseTask):
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
    first_address = MallAddressAsset(
        member_username=MALL_LOGIN_USERNAME,
        name="Avery Brooks",
        phone_number="5550101068",
        province="New York State",
        city="New York City",
        region="Manhattan Borough",
        detail_address="12 Hudson Street Apt 1",
        post_code="100010",
        default_status=False,
    )
    second_address = MallAddressAsset(
        member_username=MALL_LOGIN_USERNAME,
        name=SECOND_RECEIVER,
        phone_number="5550101069",
        province="New York State",
        city="New York City",
        region="Queens Borough",
        detail_address="44 Queens Boulevard Apt 2",
        post_code="100080",
        default_status=False,
    )
    assets = (login_user, first_address, second_address)

    goal = (
        "Open Mall and buy one HUAWEI Mate 80 Pro. When choosing the shipping address, "
        "use Morgan Carter's saved Queens address, then pay with Alipay."
    )

    def criteria(self):
        return [
            MallCheckoutOrderCreated(
                member_username=MALL_LOGIN_USERNAME,
                product_sn=PRODUCT_SN,
                quantity=1,
                expected_status=1,
                receiver_name=SECOND_RECEIVER,
            )
        ]
