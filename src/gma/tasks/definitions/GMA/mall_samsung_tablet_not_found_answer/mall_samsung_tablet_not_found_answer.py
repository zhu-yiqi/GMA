from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallAddressAsset, MallMemberAsset
from gma.tasks.base import BaseTask
from gma.tasks.definitions.tests.mall._criteria import MallCheckoutOrderCreated


PRODUCT_SN = "1258669"
RECEIVER = "Morgan Carter"


class MallSamsungTabletNotFoundAnswerTask(BaseTask):
    apps = {"Mall"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent reports that no Samsung tablet is available and asks what to do, answer exactly: "
        "Buy one default HUAWEI Mate 80 Pro Mall listing using Morgan Carter's Queens address instead and pay with Alipay; I have no color or storage preference. Do not answer unrelated questions."
    )
    login_user = MallMemberAsset(
        username=MALL_LOGIN_USERNAME,
        password="123456",
        nickname=MALL_LOGIN_NICKNAME,
        phone=MALL_LOGIN_PHONE,
        city=MALL_LOGIN_CITY,
        status=1,
    )
    address = MallAddressAsset(
        member_username=MALL_LOGIN_USERNAME,
        name=RECEIVER,
        phone_number="5550101069",
        province="New York State",
        city="New York City",
        region="Queens Borough",
        detail_address="44 Queens Boulevard Apt 2",
        post_code="100080",
        default_status=True,
    )
    assets = (login_user, address)
    goal = "Open Mall and buy one Samsung tablet using my default address and pay with Alipay."

    def criteria(self):
        return [MallCheckoutOrderCreated(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, quantity=1, expected_status=1, receiver_name=RECEIVER)]
