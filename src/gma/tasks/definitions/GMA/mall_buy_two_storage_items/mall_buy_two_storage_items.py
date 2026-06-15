from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallAddressAsset, MallMemberAsset
from gma.tasks.base import BaseTask
from gma.tasks.definitions.tests.mall._criteria import MallCheckoutOrderCreated


SSD_SN = "YMTCPC550"
CARD_SN = "zhitaiprosdcard"
FIRST_ADDRESS = "First Storage Address"
SECOND_ADDRESS = "Second Storage Address"


class MallBuyTwoStorageItemsTask(BaseTask):
    apps = {"Mall"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent asks which hard drive type to buy, answer exactly: "
        "Buy one default Commercial consumer-grade PCIe 5.0 NVMe SSD listing and pay with Alipay. Do not provide unrelated information."
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
            phone_number="5550101071",
            province="New York State",
            city="New York City",
            region="Manhattan Borough",
            detail_address="Storage First Room 1",
            post_code="100010",
        ),
        MallAddressAsset(
            member_username=MALL_LOGIN_USERNAME,
            name=SECOND_ADDRESS,
            phone_number="5550101072",
            province="New York State",
            city="New York City",
            region="Queens Borough",
            detail_address="Storage Second Room 2",
            post_code="100080",
        ),
    )
    goal = (
        "Open Mall and buy one hard drive using my first address and pay with Alipay. Also buy one ZhiTai PRO "
        "professional high-speed memory card using my second address and pay with Alipay."
    )

    def criteria(self):
        return [
            MallCheckoutOrderCreated(
                member_username=MALL_LOGIN_USERNAME,
                product_sn=SSD_SN,
                quantity=1,
                expected_status=1,
                receiver_name=FIRST_ADDRESS,
            ),
            MallCheckoutOrderCreated(
                member_username=MALL_LOGIN_USERNAME,
                product_sn=CARD_SN,
                quantity=1,
                expected_status=1,
                receiver_name=SECOND_ADDRESS,
            ),
        ]
