from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallAddressAsset, MallMemberAsset
from gma.evaluation import AnswerEquals
from gma.tasks.base import BaseTask
from gma.tasks.definitions.tests.mall._criteria import MallCheckoutOrderCreated


CABLE_SN = "5689"
FIRST_ADDRESS = "Avery First Address"
EXPECTED_ANSWER = (
    "Phones subcategories: Mobile Phones, Phone Accessories, Photography & Video, "
    "Audio & Video Entertainment, Digital Accessories; Self-powered charger with cable price: 169.00; "
    "oneplus Fast-charging data cable price: 99.00"
)


class MallPhoneCategoriesCablePriceOrderTask(BaseTask):
    apps = {"Mall"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
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
            phone_number="5550101074",
            province="New York State",
            city="New York City",
            region="Manhattan Borough",
            detail_address="First Address Room 401",
            post_code="100010",
            default_status=True,
        ),
    )
    goal = (
        "Open Mall and check all subcategories under Phones. Then find the Phone Accessories whose names include \"cable\" and keep their prices for your final response. "
        "Buy one default oneplus Fast-charging data cable using the first address and pay with Alipay. "
        "After the purchase, answer exactly using this format: \"Phones subcategories: <names separated by comma and space>; Self-powered charger with cable price: <price>; oneplus Fast-charging data cable price: <price>\"."
    )

    def criteria(self):
        return [
            AnswerEquals(EXPECTED_ANSWER),
            MallCheckoutOrderCreated(
                member_username=MALL_LOGIN_USERNAME,
                product_sn=CABLE_SN,
                quantity=1,
                expected_status=1,
                receiver_name=FIRST_ADDRESS,
            ),
        ]
