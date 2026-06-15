from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallAddressAsset, MallMemberAsset
from gma.tasks.base import BaseTask
from gma.tasks.definitions.tests.mall._criteria import MallCheckoutOrderCreated


IPHONE_17_PRO_SN = "JNW6WYGVKF"
FIRST_ADDRESS = "IPhone First Address"


class MallAskUserBuyIphone17ProTask(BaseTask):
    apps = {"Mall"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent asks which iPhone model to buy, answer exactly: Buy one iPhone 17 Pro; "
        "I only want the default Mall listing, with no color or storage preference. Do not provide unrelated information."
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
        MallAddressAsset(
            member_username=MALL_LOGIN_USERNAME,
            name=FIRST_ADDRESS,
            phone_number="5550101066",
            province="New York State",
            city="New York City",
            region="Manhattan Borough",
            detail_address="IPhone First Address Room 1",
            post_code="100010",
            default_status=True,
        ),
    )
    goal = "Open Mall and buy an iPhone using my first address and pay with Alipay."

    def criteria(self):
        return [
            MallCheckoutOrderCreated(
                member_username=MALL_LOGIN_USERNAME,
                product_sn=IPHONE_17_PRO_SN,
                quantity=1,
                expected_status=1,
                receiver_name=FIRST_ADDRESS,
            )
        ]
