from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallAddressAsset, MallMemberAsset
from gma.tasks.base import BaseTask
from gma.evaluation.checks.mall import MallCheckoutOrderCreated


CHEAPEST_LENOVO_LAPTOP_SN = "AK-83F30081CD"
FIRST_ADDRESS = "Lenovo First Address"


class MallBuyCheapestLenovoLaptopTask(BaseTask):
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
            phone_number="5550101067",
            province="New York State",
            city="New York City",
            region="Manhattan Borough",
            detail_address="Lenovo First Address Room 1",
            post_code="100010",
            default_status=True,
        ),
    )
    goal = "Open Mall and buy the cheapest Lenovo laptop using my first address and pay with Alipay."

    def criteria(self):
        return [
            MallCheckoutOrderCreated(
                member_username=MALL_LOGIN_USERNAME,
                product_sn=CHEAPEST_LENOVO_LAPTOP_SN,
                quantity=1,
                expected_status=1,
                receiver_name=FIRST_ADDRESS,
            )
        ]
